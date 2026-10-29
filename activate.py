#!/usr/bin/env python3
"""Prepare Steam to apply a pending ubuntu12 offline manifest (one launch)."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

STEAM_CFG = Path("steam.cfg")
RT64 = "steam_client_steamrt64"


def quarantine_rt64(pkg: Path) -> None:
    q = pkg / "_quarantine_steamrt64"
    q.mkdir(exist_ok=True)
    moved = 0
    for name in (f"{RT64}.manifest", f"{RT64}.installed"):
        p = pkg / name
        if p.is_file():
            shutil.move(p, q / name)
            moved += 1
            print(f"quarantine: {name}")
    for p in sorted(pkg.glob(f"{RT64} (*)")):
        shutil.move(p, q / p.name)
        moved += 1
        print(f"quarantine: {p.name}")
    if not moved:
        print("quarantine: nothing to move (ok)")


def activate(steam_dir: Path, quarantine: bool, remove_cfg: bool) -> None:
    pkg = steam_dir / "package"
    u12 = pkg / "steam_client_ubuntu12.manifest"
    if not u12.is_file():
        raise SystemExit(f"missing {u12} — run install first")
    marker = next(iter(pkg.glob("steam_client_ubuntu12 (*)")), None)
    if marker is None and not (pkg / "steam_client_ubuntu12.installed").is_file():
        raise SystemExit(
            "no pending ubuntu12 marker — re-run install or archive steam_client_ubuntu12.installed"
        )
    if quarantine:
        quarantine_rt64(pkg)
    cfg = steam_dir / STEAM_CFG
    if remove_cfg and cfg.is_file():
        cfg.unlink()
        print(f"removed {cfg} (BootStrapperInhibitAll was blocking extract)")
    log = steam_dir / "logs/bootstrap_log.txt"
    print(
        "\nLaunch Steam normally (no -forcesteamupdate). Expect in bootstrap log:\n"
        "  uninstalled manifest found in .../steam_client_ubuntu12 (1)\n"
        "  Found pending update -> Extracting package...\n"
        f"Then: grep -E 'updater built|buildid=' {log} | tail -5\n"
        "After Sep 2024 is confirmed, lock updates: ./downgrade lock-updates"
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Enable pending ubuntu12 offline extract")
    p.add_argument("--steam-dir", type=Path, default=Path.home() / ".steam/debian-installation")
    p.add_argument("--no-quarantine-rt64", action="store_true")
    p.add_argument("--keep-steam-cfg", action="store_true")
    args = p.parse_args()
    activate(args.steam_dir, quarantine=not args.no_quarantine_rt64, remove_cfg=not args.keep_steam_cfg)


if __name__ == "__main__":
    main()
