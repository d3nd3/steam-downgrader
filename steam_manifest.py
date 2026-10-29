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


def verify_sha256(path: Path, expected: str | None) -> bool:
    if not expected:
        return True
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()
