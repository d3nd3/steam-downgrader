#!/usr/bin/env python3
"""Wayback fetch with SteamTracking/Fastly fallback for missing Archive blobs."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from steam_manifest import cache_missing_artifacts, load_manifest, require_cache_complete

ROOT = Path(__file__).resolve().parent
WAYBACK_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})\d*$")


def wayback_to_calendar(ts: str) -> str | None:
    m = WAYBACK_RE.match(ts.strip())
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch client cache (Wayback, then CDN if needed)")
    p.add_argument("--wayback-date", required=True)
    p.add_argument("--calendar-date", help="YYYY-MM-DD for SteamTracking fallback (default: parse from wayback ts)")
    p.add_argument("--manifest", default="steam_client_ubuntu12")
    p.add_argument("--cache", type=Path, default=ROOT / "cache")
    p.add_argument("--jobs", type=int, default=6)
    p.add_argument("--no-tracking-fallback", action="store_true")
    args = p.parse_args()

    fetch_py = [sys.executable, str(ROOT / "fetch.py"), "--cache", str(args.cache), "--manifest", args.manifest, "--jobs", str(args.jobs)]
    r = subprocess.run([*fetch_py, "--wayback-date", args.wayback_date])
    cal = args.calendar_date or wayback_to_calendar(args.wayback_date)
    if r.returncode == 0:
        ms = sorted(args.cache.glob(f"*/{args.manifest}.manifest"), key=lambda p: p.stat().st_mtime)
        if ms:
            require_cache_complete(ms[-1].parent, args.manifest)
        print(f"cache ready (Wayback): {ms[-1].parent if ms else args.cache}")
        return 0

    if args.no_tracking_fallback or not cal:
        print("Wayback fetch failed and no calendar date for fallback.", file=sys.stderr)
        return r.returncode or 1

    print(f"Wayback incomplete — trying SteamTracking + Fastly for {cal} …", file=sys.stderr)
    tr = subprocess.run(
        [sys.executable, str(ROOT / "fetch_steamtracking.py"), "--cache", str(args.cache), "--date", cal, "--manifest", args.manifest, "--jobs", str(args.jobs)],
    )
    if tr.returncode != 0:
        return tr.returncode
    ms = sorted(args.cache.glob(f"*/{args.manifest}.manifest"), key=lambda p: p.stat().st_mtime)
    if not ms:
        raise SystemExit("no manifest in cache after fallback")
    require_cache_complete(ms[-1].parent, args.manifest)
    _, ver, _ = load_manifest(ms[-1])
    print(f"cache ready (Fastly fill): {args.cache / ver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
