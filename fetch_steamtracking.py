#!/usr/bin/env python3
"""
Resolve ClientManifest from SteamDatabase/SteamTracking at a target date.

Port of idea from https://github.com/rares478/Steam-Downgrader (Windows + win32 manifest).
Linux uses ClientManifest/steam_client_ubuntu12; steam_client_steamrt64 has no useful history.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fetch import fetch_artifacts
from steam_manifest import parse_manifest

API = "https://api.github.com/repos/SteamDatabase/SteamTracking/commits"
RAW = "https://raw.githubusercontent.com/SteamDatabase/SteamTracking/{sha}/ClientManifest/{name}"
CDN = "https://client-update.fastly.steamstatic.com"


def github_json(url: str) -> list | dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "steam-downgrader/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def commit_before(manifest_name: str, target_date: str, max_pages: int = 40) -> tuple[str, str]:
    """Return (commit_sha, commit_iso_date) for newest commit on or before target_date."""
    target = datetime.fromisoformat(f"{target_date}T23:59:59+00:00")
    best_sha = ""
    best_dt: datetime | None = None
    for page in range(1, max_pages + 1):
        url = f"{API}?path=ClientManifest/{manifest_name}&per_page=100&page={page}"
        try:
            commits = github_json(url)
        except urllib.error.HTTPError as e:
            if e.code == 409 or e.code == 422:
                break
            raise
        if not commits:
            break
        for c in commits:
            dt = datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00"))
            if dt <= target and (best_dt is None or dt > best_dt):
                best_dt = dt
                best_sha = c["sha"]
    if not best_sha:
        raise SystemExit(f"no SteamTracking commit for {manifest_name} on/before {target_date}")
    return best_sha, best_dt.isoformat() if best_dt else ""


def download_manifest_at_commit(sha: str, manifest_name: str, dest: Path) -> None:
    url = RAW.format(sha=sha, name=manifest_name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "steam-downgrader/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = r.read().decode("utf-8", errors="replace")
    dest.write_text(text, encoding="utf-8")
    _, version, _ = parse_manifest(text)
    print(f"manifest {manifest_name} version={version} @ {sha[:12]}")


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch ubuntu12 client from SteamTracking history")
    p.add_argument("--date", required=True, help="target date YYYY-MM-DD (newest manifest on/before)")
    p.add_argument("--manifest", default="steam_client_ubuntu12")
    p.add_argument("--cache", type=Path, default=Path(__file__).resolve().parent / "cache")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--cdn-base", default=CDN)
    args = p.parse_args()

    sha, when = commit_before(args.manifest, args.date)
    print(f"commit {sha} ({when})")

    tmp = args.cache / "_steamtracking" / f"{sha[:12]}_{args.manifest}.manifest"
    download_manifest_at_commit(sha, args.manifest, tmp)
    _, version, _ = parse_manifest(tmp.read_text(encoding="utf-8"))
    version_dir = args.cache / version
    version_dir.mkdir(parents=True, exist_ok=True)
    final = version_dir / f"{args.manifest}.manifest"
    tmp.replace(final)

    fetch_artifacts(args.cdn_base, final, args.jobs, skip_existing=True, verify=True)
    print(f"cache ready: {version_dir}")


if __name__ == "__main__":
    main()
