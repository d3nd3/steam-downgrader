"""Decompress Valve .vz (VZa) blobs — LZMA body, footer CRC + size + b'zv'."""
from __future__ import annotations

import lzma
import struct
import zlib
from pathlib import Path


def decompress_vza(data: bytes) -> bytes:
    if data[:3] != b"VZa":
        raise ValueError(f"not VZa: {data[:4]!r}")
    if data[-2:] != b"zv":
        raise ValueError(f"bad footer: {data[-4:]!r}")
    flt = lzma._decode_filter_properties(lzma.FILTER_LZMA1, data[7:12])
    dec = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[flt])
    checksum, size = struct.unpack("<II", data[-10:-2])
    out = dec.decompress(data[12:-10])[:size]
    if zlib.crc32(out) & 0xFFFFFFFF != checksum:
        raise ValueError("VZa CRC mismatch")
    return out


def read_vz_path(path: Path) -> bytes:
    return decompress_vza(path.read_bytes())
