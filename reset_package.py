#!/usr/bin/env python3
"""Reset package/ to Sep cache only, then apply_mirror."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from steam_manifest import load_manifest


def reset_package(steam_dir: Path, cache_dir: Path) -> None:
    _, version, artifacts = load_manifest(cache_dir / "steam_client_ubuntu12.manifest")
    pkg = steam_dir / "package"
    keep = {a.name for a in artifacts} | {
        "steam_client_ubuntu12.manifest",
        "steam_client_steamrt64.manifest",
        "steam_client_metrics.bin",
    }
    for p in list(pkg.iterdir()):
        if p.name.startswith("_quarantine"):
            continue
        if p.is_file() and p.name not in keep and (
            p.name.startswith("steam_client") or p.suffix in (".vz", ".zip") or ".zip." in p.name
        ):
            p.unlink()
    for p in pkg.glob("steam_client*"):
        if p.is_file():
            p.unlink()
    for art in artifacts:
        shutil.copy2(cache_dir / art.name, pkg / art.name)
    m = cache_dir / "steam_client_ubuntu12.manifest"
    shutil.copy2(m, pkg / "steam_client_ubuntu12.manifest")
    shutil.copy2(m, pkg / "steam_client_steamrt64.manifest")
    print(f"package reset for version {version}, {len(artifacts)} blobs")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--steam-dir", type=Path, default=Path.home() / ".steam/debian-installation")
    p.add_argument("--cache-version-dir", type=Path, default=Path(__file__).resolve().parent / "cache/1726088054")
    args = p.parse_args()
    reset_package(args.steam_dir, args.cache_version_dir)


if __name__ == "__main__":
    main()
