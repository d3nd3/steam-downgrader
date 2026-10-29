#!/usr/bin/env python3
"""Destructive downgrade from a fetched ubuntu12 cache directory."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from steam_manifest import load_manifest

ROOT = Path(__file__).resolve().parent
_wc = os.environ.get("STEAM_DOWNGRADER_WORKING_CLIENT", "").strip()
WORKING_CLIENT = Path(_wc) if _wc else None
DEFAULT_CACHE = ROOT / "cache" / "1726088054"
DEFAULT_MANIFEST_BASENAME = "steam_client_ubuntu12"
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
    """Replace bootstrap stub with ubuntu12_32/steam from steam_ubuntu12 package."""
    import io
    import tarfile
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
        with tarfile.open(bootstrap, "r:xz") as tf:
            boot_sha = hashlib.sha256(tf.extractfile("ubuntu12_32/steam").read()).hexdigest()
    new_sha = hashlib.sha256(payload).hexdigest()
    if boot_sha and new_sha == boot_sha:
        raise SystemExit("steam_ubuntu12.zip still matches bootstrap stub — wrong cache?")
    dest.write_bytes(payload)
    dest.chmod(0o755)
    print(f"synced {dest} from cache ({new_sha[:12]}…, {len(payload)} bytes)")


def verify(
    steam_dir: Path,
    expected_build: str,
    manifest_basename: str,
    overlay_md5: str | None = None,
) -> None:
    overlay32 = steam_dir / "ubuntu12_32/gameoverlayrenderer.so"
    overlay64 = steam_dir / "ubuntu12_64/gameoverlayrenderer.so"
    if overlay_md5:
        for label, path in (("ubuntu12_64", overlay64), ("ubuntu12_32", overlay32)):
            if not path.is_file():
                continue
            got = hashlib.md5(path.read_bytes()).hexdigest()
            if got == overlay_md5.lower():
                print(f"overlay md5 OK on {label} ({got})")
                break
        else:
            got64 = hashlib.md5(overlay64.read_bytes()).hexdigest() if overlay64.is_file() else "missing"
            got32 = hashlib.md5(overlay32.read_bytes()).hexdigest() if overlay32.is_file() else "missing"
            raise SystemExit(f"overlay md5 mismatch (64={got64}, 32={got32}, want {overlay_md5})")
    overlay = overlay64 if overlay64.is_file() else overlay32
    client = steam_dir / "linux64/steamclient.so"
    if not overlay.is_file():
        raise SystemExit("missing ubuntu12_*/gameoverlayrenderer.so")
    if not client.is_file():
        raise SystemExit("missing linux64/steamclient.so")
    if WORKING_CLIENT and WORKING_CLIENT.is_file():

        def sha256_file(p: Path) -> str:
            h = hashlib.sha256()
            with p.open("rb") as f:
                for c in iter(lambda: f.read(1 << 20), b""):
                    h.update(c)
            return h.hexdigest()

        if sha256_file(client) != sha256_file(WORKING_CLIENT):
            raise SystemExit("linux64/steamclient.so != working_steamclient.so")
    ver = (steam_dir / f"package/{manifest_basename}.manifest").read_text(encoding="utf-8", errors="replace")
    if expected_build not in ver:
        raise SystemExit(f"manifest missing build {expected_build}")
    if (steam_dir / "steamrt64").is_dir():
        raise SystemExit("remove steamrt64/ before launch")
    bootstrap = steam_dir / "bootstrap.tar.xz"
    if bootstrap.is_file():
        import tarfile

        def sha256_bytes(b: bytes) -> str:
            return hashlib.sha256(b).hexdigest()

        with tarfile.open(bootstrap, "r:xz") as tf:
            m = tf.getmember("ubuntu12_32/steam")
            boot_steam = sha256_bytes(tf.extractfile(m).read())
        cur_steam = sha256_bytes((steam_dir / "ubuntu12_32/steam").read_bytes())
        if boot_steam == cur_steam:
            print(
                "WARN: ubuntu12_32/steam is still the bootstrap stub (often Sep 2025). "
                "Run sync_steam_executable or re-run force-sep2024 after fix."
            )
    print(f"OK: client build {expected_build}, overlay + steamclient verified")


def write_sep_launcher(steam_dir: Path) -> None:
    default = Path.home() / ".steam/debian-installation"
    if steam_dir.resolve() != default.resolve():
        print(
            f"NOTE: custom STEAM_DIR={steam_dir} — export STEAM_DIR when running ./sep-steam",
            file=sys.stderr,
        )
    SEP_STEAM.write_text(
        f"""#!/usr/bin/env bash
# Generated launcher — gitignored; do not commit.
# Legacy ubuntu12_32 path (no steamrt64).
set -euo pipefail
STEAMDIR="${{STEAM_DIR:-$HOME/.steam/debian-installation}}"
rm -f "$STEAMDIR/.steam-enable-steamrt64-client"
export STEAM_FORCE_CLIENT=ubuntu12_32
exec {LAUNCHER} "$@"
""",
        encoding="utf-8",
    )
    SEP_STEAM.chmod(0o755)
    print(f"launcher: {SEP_STEAM}")


def steam_running(steam_dir: Path) -> bool:
    r = subprocess.run(
        ["pgrep", "-f", f"{steam_dir}/"],
        capture_output=True,
        check=False,
    )
    return r.returncode == 0


def confirm_destructive(steam_dir: Path, build: str, yes: bool) -> None:
    if yes or os.environ.get("STEAM_DOWNGRADER_YES") == "1":
        return
    if steam_running(steam_dir):
        print("ERROR: Steam still running — quit completely and retry.", file=sys.stderr)
        raise SystemExit(1)
    print(f"This will WIPE client trees under {steam_dir} and install build {build}.")
    print("Games in steamapps/ are kept; client_backup_* is created first.")
    try:
        answer = input("Type 'yes' to continue: ").strip().lower()
    except EOFError:
        answer = ""
    if answer != "yes":
        raise SystemExit("aborted")


def install_bootstrap(steam_dir: Path) -> None:
    archive = steam_dir / "bootstrap.tar.xz"
    if not archive.is_file():
        raise SystemExit(f"missing {archive}")
    subprocess.run(["tar", "-xf", str(archive), "-C", str(steam_dir)], check=True)
    print(f"extracted bootstrap -> {steam_dir}/ubuntu12_32/steam")


def main() -> None:
    p = argparse.ArgumentParser(description="Destructive downgrade from cache/<build>/")
    p.add_argument("--steam-dir", type=Path, default=Path.home() / ".steam/debian-installation")
    p.add_argument("--cache-version-dir", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--manifest-basename", default=DEFAULT_MANIFEST_BASENAME)
    p.add_argument("--expected-build", help="manifest build id (default: cache dir name)")
    p.add_argument("--overlay-md5", help="verify ubuntu12_*/gameoverlayrenderer.so md5")
    p.add_argument("--skip-extract", action="store_true")
    p.add_argument("-y", "--yes", action="store_true", help="skip confirmation (or STEAM_DOWNGRADER_YES=1)")
    args = p.parse_args()
    if not args.cache_version_dir.is_dir():
        raise SystemExit(f"fetch cache first: {args.cache_version_dir}")
    manifest_name = f"{args.manifest_basename}.manifest"
    manifest_path = args.cache_version_dir / manifest_name
    if not manifest_path.is_file():
        raise SystemExit(f"missing {manifest_path}")
    _, build_from_manifest, _ = load_manifest(manifest_path)
    expected_build = args.expected_build or args.cache_version_dir.name
    if expected_build != build_from_manifest:
        print(f"WARN: cache dir name {expected_build} != manifest build {build_from_manifest}", file=sys.stderr)
        expected_build = build_from_manifest

    subprocess.run(["pkill", "-f", "debian-installation/ubuntu12_32/steam"], check=False)
    subprocess.run(["pkill", "-f", "debian-installation/steamrt64/steam"], check=False)
    time.sleep(2)

    if args.skip_extract:
        lock(args.steam_dir)
        verify(args.steam_dir, expected_build, args.manifest_basename, args.overlay_md5)
        write_sep_launcher(args.steam_dir)
        print(f"\nStart Steam: {SEP_STEAM}")
        return

    confirm_destructive(args.steam_dir, expected_build, args.yes)

    subprocess.run([sys.executable, str(ROOT / "nuke_client.py"), "--steam-dir", str(args.steam_dir)], check=True)
    install_bootstrap(args.steam_dir)
    lock(args.steam_dir)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "reset_package.py"),
            "--steam-dir",
            str(args.steam_dir),
            "--cache-version-dir",
            str(args.cache_version_dir),
            "--manifest-basename",
            args.manifest_basename,
        ],
        check=True,
    )
    clear_package_markers(args.steam_dir)
    strip_package_blobs(args.steam_dir)

    if not args.skip_extract:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "apply_mirror.py"),
                "--steam-dir",
                str(args.steam_dir),
                "--cache-version-dir",
                str(args.cache_version_dir),
                "--manifest-basename",
                args.manifest_basename,
                "--launcher",
                str(LAUNCHER),
            ],
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
    verify(args.steam_dir, expected_build, args.manifest_basename, args.overlay_md5)
    write_sep_launcher(args.steam_dir)
    print("\nUse ONLY this to start Steam while testing:")
    print(f"  {SEP_STEAM}")
    print(f"Help → About should show build {expected_build} on ubuntu12_32 path.")


if __name__ == "__main__":
    main()
