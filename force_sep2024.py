#!/usr/bin/env python3
"""Full destructive downgrade to Sep 2024 ubuntu12 client (build 1726088054)."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_wc = os.environ.get("STEAM_DOWNGRADER_WORKING_CLIENT", "").strip()
WORKING_CLIENT = Path(_wc) if _wc else None
CACHE = ROOT / "cache" / "1726088054"
MANIFEST = "steam_client_ubuntu12.manifest"
SEP_BUILD = "1726088054"
STEAM_CFG = """BootStrapperInhibitAll=enable
BootStrapperForceSelfUpdate=disable
"""
LAUNCHER = Path("/usr/games/steam")
SEP_STEAM = ROOT / "sep-steam"


def lock(steam_dir: Path) -> None:
    (steam_dir / "steam.cfg").write_text(STEAM_CFG, encoding="utf-8")


def clear_package_markers(steam_dir: Path) -> None:
    pkg = steam_dir / "package"
    for p in list(pkg.glob("steam_client*.installed")) + list(pkg.glob("steam_client* (*)")):
        p.unlink()
    (pkg / "steam_client_metrics.bin").unlink(missing_ok=True)


def strip_package_blobs(steam_dir: Path) -> None:
    """Remove cached blobs so bootstrap must re-download + extract (installed version 0)."""
    pkg = steam_dir / "package"
    n = 0
    for p in pkg.iterdir():
        if not p.is_file() or p.name.endswith(".manifest"):
            continue
        if p.name.startswith("steam_client"):
            continue
        if ".vz" in p.name or ".zip" in p.name:
            p.unlink()
            n += 1
    print(f"stripped {n} package blobs for forced extract")


from vzip import read_vz_path


def sync_steam_executable(steam_dir: Path, cache_version_dir: Path) -> None:
    """Replace bootstrap stub with ubuntu12_32/steam from Sep steam_ubuntu12 package."""
    import hashlib
    import io
    import zipfile

    vz = next(cache_version_dir.glob("steam_ubuntu12.zip.vz.*"), None)
    if not vz:
        raise SystemExit(f"missing steam_ubuntu12.zip.vz in {cache_version_dir}")
    with zipfile.ZipFile(io.BytesIO(read_vz_path(vz))) as zf:
        member = "ubuntu12_32/steam"
        if member not in zf.namelist():
            raise SystemExit(f"{member} not in {vz.name}")
        payload = zf.read(member)
    dest = steam_dir / "ubuntu12_32/steam"
    boot_sha = None
    bootstrap = steam_dir / "bootstrap.tar.xz"
    if bootstrap.is_file():
        import tarfile

        with tarfile.open(bootstrap, "r:xz") as tf:
            boot_sha = hashlib.sha256(tf.extractfile("ubuntu12_32/steam").read()).hexdigest()
    new_sha = hashlib.sha256(payload).hexdigest()
    if boot_sha and new_sha == boot_sha:
        raise SystemExit("steam_ubuntu12.zip still matches bootstrap stub — wrong cache?")
    dest.write_bytes(payload)
    dest.chmod(0o755)
    print(f"synced {dest} from cache ({new_sha[:12]}…, {len(payload)} bytes)")


def verify(steam_dir: Path) -> None:
    overlay = steam_dir / "ubuntu12_32/gameoverlayrenderer.so"
    client = steam_dir / "linux64/steamclient.so"
    if not overlay.is_file():
        raise SystemExit("missing ubuntu12_32/gameoverlayrenderer.so")
    if time.gmtime(overlay.stat().st_mtime).tm_year != 2024:
        raise SystemExit("overlay not from Sep 2024 build")
    if not client.is_file():
        raise SystemExit("missing linux64/steamclient.so")
    if WORKING_CLIENT and WORKING_CLIENT.is_file():

        def sha(p: Path) -> str:
            import hashlib

            h = hashlib.sha256()
            with p.open("rb") as f:
                for c in iter(lambda: f.read(1 << 20), b""):
                    h.update(c)
            return h.hexdigest()

        if sha(client) != sha(WORKING_CLIENT):
            raise SystemExit("linux64/steamclient.so != working_steamclient.so")
    ver = (steam_dir / "package/steam_client_ubuntu12.manifest").read_text(encoding="utf-8", errors="replace")
    if SEP_BUILD not in ver:
        raise SystemExit("manifest not 1726088054")
    if (steam_dir / "steamrt64").is_dir():
        raise SystemExit("remove steamrt64/ before launch")
    bootstrap = steam_dir / "bootstrap.tar.xz"
    if bootstrap.is_file():
        import hashlib
        import tarfile

        def sha_bytes(b: bytes) -> str:
            return hashlib.sha256(b).hexdigest()

        with tarfile.open(bootstrap, "r:xz") as tf:
            m = tf.getmember("ubuntu12_32/steam")
            boot_steam = sha_bytes(tf.extractfile(m).read())
        cur_steam = sha_bytes((steam_dir / "ubuntu12_32/steam").read_bytes())
        if boot_steam == cur_steam:
            print(
                "WARN: ubuntu12_32/steam is still the bootstrap stub (often Sep 2025). "
                "Run sync_steam_executable or re-run force-sep2024 after fix."
            )
    print(f"OK: Sep 2024 client (build {SEP_BUILD}), overlay + steamclient verified")


def write_sep_launcher(steam_dir: Path) -> None:
    SEP_STEAM.write_text(
        f"""#!/usr/bin/env bash
# Sep 2024 client — forces legacy ubuntu12_32 path (no steamrt64).
set -euo pipefail
STEAMDIR="{steam_dir}"
rm -f "$STEAMDIR/.steam-enable-steamrt64-client"
export STEAM_FORCE_CLIENT=ubuntu12_32
exec {LAUNCHER} "$@"
""",
        encoding="utf-8",
    )
    SEP_STEAM.chmod(0o755)
    print(f"launcher: {SEP_STEAM}")


def install_bootstrap(steam_dir: Path) -> None:
    archive = steam_dir / "bootstrap.tar.xz"
    if not archive.is_file():
        raise SystemExit(f"missing {archive}")
    subprocess.run(["tar", "-xf", str(archive), "-C", str(steam_dir)], check=True)
    print(f"extracted bootstrap -> {steam_dir}/ubuntu12_32/steam")


def main() -> None:
    p = argparse.ArgumentParser(description="Destructive Sep 2024 downgrade")
    p.add_argument("--steam-dir", type=Path, default=Path.home() / ".steam/debian-installation")
    p.add_argument("--cache-version-dir", type=Path, default=CACHE)
    p.add_argument("--skip-extract", action="store_true")
    args = p.parse_args()
    if not args.cache_version_dir.is_dir():
        raise SystemExit(f"fetch cache first: {args.cache_version_dir}")

    subprocess.run(["pkill", "-f", "debian-installation/ubuntu12_32/steam"], check=False)
    subprocess.run(["pkill", "-f", "debian-installation/steamrt64/steam"], check=False)
    time.sleep(2)

    if args.skip_extract:
        lock(args.steam_dir)
        verify(args.steam_dir)
        write_sep_launcher(args.steam_dir)
        print(f"\nStart Steam: {SEP_STEAM}")
        return

    subprocess.run([sys.executable, str(ROOT / "nuke_client.py"), "--steam-dir", str(args.steam_dir)], check=True)
    install_bootstrap(args.steam_dir)
    lock(args.steam_dir)
    subprocess.run(
        [sys.executable, str(ROOT / "reset_package.py"), "--steam-dir", str(args.steam_dir), "--cache-version-dir", str(args.cache_version_dir)],
        check=True,
    )
    clear_package_markers(args.steam_dir)
    strip_package_blobs(args.steam_dir)

    if not args.skip_extract:
        subprocess.run(
            [sys.executable, str(ROOT / "apply_mirror.py"), "--steam-dir", str(args.steam_dir), "--cache-version-dir", str(args.cache_version_dir), "--launcher", str(LAUNCHER)],
            check=True,
        )

    # apply_mirror may leave steamrt64; remove again and re-verify ubuntu12 tree
    rt = args.steam_dir / "steamrt64"
    if rt.is_dir():
        shutil.rmtree(rt)
        print("removed steamrt64/ after extract")
    rt32 = args.steam_dir / "steamrt32"
    if rt32.is_dir():
        shutil.rmtree(rt32)

    sync_steam_executable(args.steam_dir, args.cache_version_dir)
    verify(args.steam_dir)
    write_sep_launcher(args.steam_dir)
    print("\nUse ONLY this to start Steam while testing:")
    print(f"  {SEP_STEAM}")
    print("Help → About should show Sep 2024 when on ubuntu12_32 path.")


if __name__ == "__main__":
    main()
