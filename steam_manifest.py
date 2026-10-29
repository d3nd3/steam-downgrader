#!/usr/bin/env python3
"""Parse Steam client package manifests (VDF-like tab format)."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

VERSION_RE = re.compile(r'"version"\s+"(\d+)"')
QUOTED_RE = re.compile(r'"([^"]+)"\s+"([^"]*)"')


@dataclass(frozen=True)
class Artifact:
    name: str  # local filename under client/
    sha256: str | None
    prefer_vz: bool


def parse_manifest(text: str) -> tuple[str, str, list[Artifact]]:
    """Return (platform_tag, version, artifacts). platform_tag e.g. ubuntu12, steamrt64."""
    lines = text.splitlines()
    platform = "unknown"
    if lines and lines[0].startswith('"') and lines[0].endswith('"'):
        platform = lines[0].strip('"')
    vm = VERSION_RE.search(text)
    if not vm:
        raise ValueError("manifest has no version field")
    version = vm.group(1)

    artifacts: list[Artifact] = []
    seen: set[str] = set()
    section: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if line in ("{", "}"):
            if line == "}" and section:
                art = _section_to_artifact(section)
                if art and art.name not in seen:
                    seen.add(art.name)
                    artifacts.append(art)
                section = {}
            continue
        m = QUOTED_RE.match(line)
        if m:
            section[m.group(1)] = m.group(2)
    return platform, version, artifacts


def _section_to_artifact(section: dict[str, str]) -> Artifact | None:
    if "zipvz" in section:
        sha = section.get("sha2vz") or section.get("sha2")
        return Artifact(section["zipvz"], sha, True)
    if "file" in section:
        return Artifact(section["file"], section.get("sha2"), False)
    return None


def load_manifest(path: Path) -> tuple[str, str, list[Artifact]]:
    return parse_manifest(path.read_text(encoding="utf-8", errors="replace"))


def cache_missing_artifacts(cache_version_dir: Path, manifest_basename: str = "steam_client_ubuntu12") -> list[str]:
    manifest_path = cache_version_dir / f"{manifest_basename}.manifest"
    if not manifest_path.is_file():
        return [f"missing {manifest_path.name}"]
    _, _, artifacts = load_manifest(manifest_path)
    missing: list[str] = []
    for art in artifacts:
        p = cache_version_dir / art.name
        if not p.is_file() or p.stat().st_size == 0:
            missing.append(art.name)
    return missing


def require_cache_complete(cache_version_dir: Path, manifest_basename: str = "steam_client_ubuntu12") -> None:
    missing = cache_missing_artifacts(cache_version_dir, manifest_basename)
    if missing:
        raise SystemExit(
            f"incomplete cache {cache_version_dir} ({len(missing)} missing blobs). "
            f"Re-run fetch or ./downgrade fetch-by-date YYYY-MM-DD. First missing: {missing[0]}"
        )


def verify_sha256(path: Path, expected: str | None) -> bool:
    if not expected:
        return True
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()
