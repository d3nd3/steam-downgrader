#!/usr/bin/env python3
"""Download Steam client manifest + package blobs from a client base URL."""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from steam_manifest import load_manifest, parse_manifest, verify_sha256

DEFAULT_WAYBACK = "http://web.archive.org/web/{date}if_/media.steampowered.com/client"
DEFAULT_LIVE = "https://client-update.fastly.steamstatic.com"


def client_url(base: str, name: str) -> str:
    return f"{base.rstrip('/')}/{name}"


def download(url: str, dest: Path, timeout: int = 120) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "steam_downgrader/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    dest.write_bytes(data)


def fetch_manifest(base: str, manifest_name: str, cache_dir: Path) -> Path:
    url = client_url(base, manifest_name)
    raw = cache_dir / f"{manifest_name}.downloading"
    final = cache_dir / f"{manifest_name}.manifest"
    print(f"manifest: {url}")
    download(url, raw)
    text = raw.read_text(encoding="utf-8", errors="replace")
    if text.lstrip().startswith("<!") or "404" in text[:200].lower():
        raw.unlink(missing_ok=True)
        raise SystemExit(f"manifest fetch looks like HTML/error, not VDF: {url}")
    _, version, _ = parse_manifest(text)
    version_dir = cache_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)
    dest = version_dir / f"{manifest_name}.manifest"
    raw.replace(dest)
    print(f"version={version} -> {dest}")
    return dest


def fetch_artifacts(
    base: str,
    manifest_path: Path,
    jobs: int,
    skip_existing: bool,
    verify: bool,
) -> None:
    _, version, artifacts = load_manifest(manifest_path)
    out_dir = manifest_path.parent
    assert out_dir.name == version, "manifest must live in cache/<version>/"

    def one(art) -> tuple[str, str]:
        dest = out_dir / art.name
        if skip_existing and dest.is_file() and dest.stat().st_size > 0:
            if verify and not verify_sha256(dest, art.sha256):
                pass
            else:
                return art.name, "skip"
        url = client_url(base, art.name)
        try:
            download(url, dest)
        except urllib.error.HTTPError as e:
            return art.name, f"HTTP {e.code}"
        except OSError as e:
            return art.name, str(e)
        if verify and art.sha256 and not verify_sha256(dest, art.sha256):
            return art.name, "sha256 mismatch"
        return art.name, "ok"

    ok = fail = skip = 0
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = [ex.submit(one, a) for a in artifacts]
        for fut in as_completed(futs):
            name, status = fut.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                print(f"FAIL {name}: {status}", file=sys.stderr)
    print(f"done: ok={ok} skip={skip} fail={fail} total={len(artifacts)}")


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch Steam client manifest and packages")
    p.add_argument("--manifest", default="steam_client_ubuntu12", help="manifest basename")
    p.add_argument("--cache", type=Path, default=Path(__file__).resolve().parent / "cache")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--no-verify-sha", action="store_true")
    p.add_argument("--skip-existing", action="store_true", default=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--wayback-date", help="Wayback timestamp e.g. 20240913122103")
    src.add_argument("--base-url", help="client root URL ending in /client")
    args = p.parse_args()

    if args.wayback_date:
        base = DEFAULT_WAYBACK.format(date=args.wayback_date)
    else:
        base = args.base_url.rstrip("/")

    args.cache.mkdir(parents=True, exist_ok=True)
    manifest_path = fetch_manifest(base, args.manifest, args.cache)
    fetch_artifacts(
        base,
        manifest_path,
        args.jobs,
        args.skip_existing,
        verify=not args.no_verify_sha,
    )


if __name__ == "__main__":
    main()
