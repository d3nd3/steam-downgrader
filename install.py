#!/usr/bin/env python3
"""
Stage a fetched manifest cache into Steam's package/ dir for offline extraction.

Mirrors Lightwo 'long, offline way': populate package/, invalidate .installed,
write steam.cfg, optional backup.
"""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from steam_manifest import load_manifest

STEAM_CFG = """BootStrapperInhibitAll=enable
BootStrapperForceSelfUpdate=disable
"""


def backup_package(pkg: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = pkg.parent / f"package_backup_{stamp}"
    if dest.exists():
        raise SystemExit(f"backup exists: {dest}")
    shutil.copytree(pkg, dest, symlinks=True)
    print(f"backup: {dest}")
    return dest


def invalidate_installed(pkg: Path, manifest_basename: str, extra: list[str]) -> None:
    """Remove .installed markers so Steam treats the manifest as pending."""
    names = [manifest_basename, *extra]
    for name in names:
        inst = pkg / f"{name}.installed"
        if not inst.is_file():
            continue
        slot = pkg / f"{name} (1)"
        n = 1
        while slot.exists():
            n += 1
            slot = pkg / f"{name} ({n})"
        inst.rename(slot)
        print(f"archived {inst.name} -> {slot.name}")


def install_cache(
    cache_version_dir: Path,
    manifest_basename: str,
    steam_dir: Path,
    backup: bool,
    invalidate_rt64: bool,
    lock_updates: bool,
) -> None:
    manifest_src = cache_version_dir / f"{manifest_basename}.manifest"
    if not manifest_src.is_file():
        raise SystemExit(f"missing {manifest_src}")

    platform, version, artifacts = load_manifest(manifest_src)
    pkg = steam_dir / "package"
    if not pkg.is_dir():
        raise SystemExit(f"no package dir: {pkg}")

    if backup:
        backup_package(pkg)

    copied = 0
    for art in artifacts:
        src = cache_version_dir / art.name
        if not src.is_file():
            print(f"WARN missing blob (fetch incomplete?): {art.name}")
            continue
        dst = pkg / art.name
        if dst.is_file() and dst.stat().st_size == src.stat().st_size:
            continue
        shutil.copy2(src, dst)
        copied += 1

    dst_manifest = pkg / f"{manifest_basename}.manifest"
    shutil.copy2(manifest_src, dst_manifest)
    print(f"manifest -> {dst_manifest} (platform={platform} version={version})")

    extra = ["steam_client_steamrt64"] if invalidate_rt64 else []
    invalidate_installed(pkg, manifest_basename, extra)

    if lock_updates:
        cfg = steam_dir / "steam.cfg"
        cfg.write_text(STEAM_CFG, encoding="utf-8")
        print(f"wrote {cfg}")
    log = steam_dir / "logs/bootstrap_log.txt"
    print(
        "\nRun: ./downgrade activate-pending   (removes steam.cfg, quarantines steamrt64)\n"
        "Then exit Steam and start normally (not -forcesteamupdate).\n"
        "On 'Extracting package...' you may Cancel once (Lightwo), delete package/tmp, start again.\n"
        f"Verify: grep -E 'updater built|buildid=' {log} | tail -5"
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Install cached Steam packages offline")
    p.add_argument("--cache-version-dir", type=Path, required=True, help="cache/<version>/")
    p.add_argument(
        "--manifest-basename",
        default="steam_client_ubuntu12",
        help="e.g. steam_client_ubuntu12 or steam_client_steamrt64",
    )
    p.add_argument(
        "--steam-dir",
        type=Path,
        default=Path.home() / ".steam/debian-installation",
    )
    p.add_argument("--no-backup", action="store_true")
    p.add_argument(
        "--no-invalidate-steamrt64",
        action="store_true",
        help="do not archive steam_client_steamrt64.installed (prefer activate-pending quarantine)",
    )
    p.add_argument(
        "--lock-updates-after",
        action="store_true",
        help="write steam.cfg immediately (blocks extract — usually wrong)",
    )
    args = p.parse_args()
    install_cache(
        args.cache_version_dir,
        args.manifest_basename,
        args.steam_dir,
        backup=not args.no_backup,
        invalidate_rt64=not args.no_invalidate_steamrt64,
        lock_updates=args.lock_updates_after,
    )


if __name__ == "__main__":
    main()
