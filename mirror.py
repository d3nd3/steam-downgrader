#!/usr/bin/env python3
"""
Local HTTP mirror for -overridepackageurl.

Serves cache/<version>/ as .../client/<filename>
Optional alias: steam_client_steamrt64 -> chosen manifest file (for 2026 bootstrap).
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


class MirrorHandler(BaseHTTPRequestHandler):
    root: Path
    manifest_alias: dict[str, Path]

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        # Accept /client/foo or /web/.../client/foo
        if "/client/" in path:
            name = path.split("/client/", 1)[1].strip("/")
        else:
            name = path.strip("/").split("/")[-1]
        if not name or ".." in name:
            self.send_error(400)
            return
        if name in self.manifest_alias:
            file_path = self.manifest_alias[name]
        else:
            file_path = self.root / name
        if not file_path.is_file():
            self.send_error(404, explain=f"not in mirror: {name}")
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    p = argparse.ArgumentParser(description="Serve Steam client cache for overridepackageurl")
    p.add_argument("--cache-version-dir", type=Path, required=True)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument(
        "--alias-steamrt64-from",
        help="serve this file for GET steam_client_steamrt64 (basename only)",
    )
    p.add_argument(
        "--alias-ubuntu12-from",
        help="serve this file for GET steam_client_ubuntu12 (basename only)",
    )
    args = p.parse_args()
    root = args.cache_version_dir.resolve()
    aliases: dict[str, Path] = {}

    def add_alias(manifest_name: str, src_name: str | None) -> None:
        if not src_name:
            return
        src = root / src_name
        if not src.is_file():
            raise SystemExit(f"alias source missing: {src}")
        aliases[manifest_name] = src

    add_alias("steam_client_steamrt64", args.alias_steamrt64_from)
    add_alias("steam_client_ubuntu12", args.alias_ubuntu12_from)

    handler = MirrorHandler
    handler.root = root
    handler.manifest_alias = aliases
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    base = f"http://127.0.0.1:{args.port}/client"
    print(f"mirror root={root}")
    print(f"overridepackageurl: {base}")
    for k, v in aliases.items():
        print(f"alias: {k} ->", v.name)
    print("Block CDN fallback while testing (/etc/hosts) — see README")
    srv.serve_forever()


if __name__ == "__main__":
    main()
