#!/usr/bin/env python3
"""Apply Sep cache via local mirror + force update (Oct 2026 bootstrap path)."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKING_CLIENT = ROOT.parent / "working_steamclient.so"
CACHE_VER = ROOT / "cache" / "1726088054"
MANIFEST = "steam_client_ubuntu12.manifest"
PORT = 8765
MIRROR_URL = f"http://127.0.0.1:{PORT}/client"
STEAM_CFG = """BootStrapperInhibitAll=enable
BootStrapperForceSelfUpdate=disable
"""
DEFAULT_LAUNCHER = Path("/usr/games/steam")


def lock_updates(steam_dir: Path) -> None:
    cfg = steam_dir / "steam.cfg"
    cfg.write_text(STEAM_CFG, encoding="utf-8")
    print(f"wrote {cfg}")


def pin_package_state(steam_dir: Path, cache_dir: Path) -> None:
    """Keep ubuntu12 track consistent so the next launch does not hit Fastly."""
    pkg = steam_dir / "package"
    src_manifest = cache_dir / MANIFEST
    shutil.copy2(src_manifest, pkg / "steam_client_ubuntu12.manifest")
    shutil.copy2(src_manifest, pkg / "steam_client_steamrt64.manifest")
    rt = pkg / "steam_client_steamrt64.installed"
    u12 = pkg / "steam_client_ubuntu12.installed"
    if rt.is_file():
        shutil.copy2(rt, u12)
    elif u12.is_file() and not rt.is_file():
        shutil.copy2(u12, rt)
    for name in ("steam_client_ubuntu12", "steam_client_steamrt64"):
        for stale in pkg.glob(f"{name} (*)"):
            stale.unlink()
    print("pinned package manifests + synced .installed markers")


def main() -> None:
    p = argparse.ArgumentParser(description="Downgrade via mirror (Sep 2024 ubuntu12 cache)")
    p.add_argument("--steam-dir", type=Path, default=Path.home() / ".steam/debian-installation")
    p.add_argument("--cache-version-dir", type=Path, default=CACHE_VER)
    p.add_argument("--launcher", type=Path, default=DEFAULT_LAUNCHER)
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--reset-package", action="store_true", help="wipe conflicting package blobs first")
    args = p.parse_args()
    steam_bin = args.steam_dir / "ubuntu12_32/steam"
    log = args.steam_dir / "logs/bootstrap_log.txt"
    if not steam_bin.is_file():
        raise SystemExit(f"missing {steam_bin} — extract bootstrap.tar.xz first")
    if not args.launcher.is_file():
        raise SystemExit(f"missing launcher {args.launcher} (set --launcher)")

    if args.reset_package:
        subprocess.run(
            [sys.executable, str(ROOT / "reset_package.py"), "--steam-dir", str(args.steam_dir), "--cache-version-dir", str(args.cache_version_dir)],
            check=True,
        )

    lock_updates(args.steam_dir)
    lines_before = log.read_text(encoding="utf-8", errors="replace").count("\n") if log.is_file() else 0

    mirror = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "mirror.py"),
            "--cache-version-dir",
            str(args.cache_version_dir),
            "--port",
            str(args.port),
            "--alias-steamrt64-from",
            MANIFEST,
            "--alias-ubuntu12-from",
            MANIFEST,
        ],
        cwd=ROOT,
    )
    time.sleep(1)
    try:
        subprocess.run(
            [
                str(args.launcher),
                "-overridepackageurl",
                MIRROR_URL,
                "-forcesteamupdate",
                "-forcepackagedownload",
                "-exitsteam",
            ],
            check=False,
        )
    finally:
        mirror.terminate()
        mirror.wait(timeout=5)

    text = log.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = text[lines_before:]
    ok = any("1726088054" in ln for ln in tail) and any("Update complete" in ln for ln in tail)
    if not ok:
        raise SystemExit("downgrade did not finish — see bootstrap_log.txt")
    pin_package_state(args.steam_dir, args.cache_version_dir)
    client = args.steam_dir / "linux64/steamclient.so"
    if WORKING_CLIENT.is_file() and client.is_file():
        import hashlib

        def sha(p: Path) -> str:
            h = hashlib.sha256()
            with p.open("rb") as f:
                for c in iter(lambda: f.read(1 << 20), b""):
                    h.update(c)
            return h.hexdigest()

        if sha(client) != sha(WORKING_CLIENT):
            raise SystemExit("extract did not deploy working-era steamclient.so")
    print("OK: linux64/steamclient.so matches working specimen")
    print("Launch with: ./sep-steam   (not plain /usr/games/steam unless STEAM_FORCE_CLIENT=ubuntu12_32)")


if __name__ == "__main__":
    main()
