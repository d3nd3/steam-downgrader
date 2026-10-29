#!/usr/bin/env python3
"""Print a human-readable report of the current Steam client install."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def md5_file(p: Path) -> str | None:
    if not p.is_file():
        return None
    return hashlib.md5(p.read_bytes()).hexdigest()


def steam_pids(steam_dir: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["pgrep", "-af", str(steam_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
        return lines[:8]
    except OSError:
        return []


def main() -> int:
    p = argparse.ArgumentParser(description="Report Steam client build and overlay paths")
    p.add_argument("--steam-dir", type=Path, default=Path.home() / ".steam/debian-installation")
    args = p.parse_args()
    sd = args.steam_dir
    sep = ROOT / "sep-steam"

    print(f"STEAM_DIR={sd}")
    running = steam_pids(sd)
    print(f"Steam processes: {len(running)}" + (" (quit before force install)" if running else " (none)"))
    for ln in running:
        print(f"  {ln[:120]}")

    cfg = sd / "steam.cfg"
    print(f"steam.cfg: {'present (updates blocked)' if cfg.is_file() else 'missing'}")
    print(f"steamrt64/: {'YES — use ./sep-steam' if (sd / 'steamrt64').is_dir() else 'no'}")

    for base in ("steam_client_ubuntu12", "steam_client_steamrt64"):
        m = sd / "package" / f"{base}.manifest"
        if m.is_file():
            text = m.read_text(encoding="utf-8", errors="replace")
            if '"version"' in text:
                for line in text.splitlines():
                    if "version" in line and "\t" in line:
                        print(f"{base}: {line.strip()}")
                        break

    bin64 = Path.home() / ".steam/bin64/gameoverlayrenderer.so"
    for label, path in (
        ("overlay ubuntu12_64", sd / "ubuntu12_64/gameoverlayrenderer.so"),
        ("overlay ubuntu12_32", sd / "ubuntu12_32/gameoverlayrenderer.so"),
        ("overlay ~/.steam/bin64", bin64),
    ):
        if path.is_file():
            print(f"{label}: md5 {md5_file(path)}  ({path.stat().st_size} bytes)")

    steam_bin = sd / "ubuntu12_32/steam"
    if steam_bin.is_file():
        print(f"ubuntu12_32/steam: {steam_bin.stat().st_size} bytes")

    if sep.is_file():
        print(f"Launcher: {sep}")
    else:
        print("Launcher: run force-wayback or force-sep2024 to create ./sep-steam")

    cache_root = ROOT / "cache"
    if cache_root.is_dir():
        manifests = sorted(cache_root.glob("*/steam_client_ubuntu12.manifest"))
        if manifests:
            print("Local cache builds:", ", ".join(p.parent.name for p in manifests[-5:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
