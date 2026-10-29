#!/usr/bin/env python3
"""Remove modern client trees so Sep ubuntu12 package extract is authoritative."""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

# Repopulated from package extract (bins_*, public_all, steamui, …)
CLIENT_TOP_DIRS = (
    "steamrt64",
    "steamrt32",
    "ubuntu12_32",
    "ubuntu12_64",
    "linux32",
    "linux64",
    "clientui",
    "friends",
    "public",
    "resource",
    "graphics",
    "controller_base",
    "tenfoot",
    "steamui",
    "siteserverui",
    "legacycompat",
    "bin",
)

MARKERS = (
    ".steam-enable-steamrt64-client",
)


def backup_client(steam_dir: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = steam_dir.parent / f"client_backup_{stamp}"
    dest.mkdir(parents=True)
    for name in (*CLIENT_TOP_DIRS, "package", "steam.cfg", "steam_dev.cfg"):
        src = steam_dir / name
        if src.exists():
            shutil.copytree(src, dest / name, symlinks=True) if src.is_dir() else shutil.copy2(src, dest / name)
    print(f"client backup: {dest}")
    return dest


def nuke_client(steam_dir: Path) -> None:
    for name in MARKERS:
        p = steam_dir / name
        if p.is_file():
            p.unlink()
    for name in CLIENT_TOP_DIRS:
        p = steam_dir / name
        if p.is_dir():
            shutil.rmtree(p)
            print(f"removed {name}/")
        elif p.is_file():
            p.unlink()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--steam-dir", type=Path, default=Path.home() / ".steam/debian-installation")
    p.add_argument("--backup", action="store_true", default=True)
    p.add_argument("--no-backup", action="store_true")
    args = p.parse_args()
    if not args.no_backup:
        backup_client(args.steam_dir)
    nuke_client(args.steam_dir)


if __name__ == "__main__":
    main()
