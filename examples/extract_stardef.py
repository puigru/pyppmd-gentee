#!/usr/bin/env python3
"""
extract_stardef.py — Extract game data from the Star Defender 1.1 installer.

Downloads stardef.exe from archive.org, then uses pyppmd's Ppmd8gDecoder
(Gentee PPMd-I variant) to decompress the embedded GEA archive.

Usage:
    python extract_stardef.py [output_dir] [--exe path/to/stardef.exe]
"""

import hashlib
import struct
import sys
import urllib.request
from pathlib import Path

import pyppmd_gentee as pyppmd

STARDEF_URL = "https://archive.org/download/stardef/stardef.exe"
STARDEF_SHA256 = "f4b71cd33db9892a5a1f63277c3a01dd4841989943d51ac6419fd20b6e6fd1ae"


def download(url: str, dest: Path, sha256: str | None = None) -> None:
    """Download a file with progress, skip if already cached."""
    if dest.exists():
        print(f"Using cached {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "pyppmd-example/1.0"})
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        data = resp.read()
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise RuntimeError("SHA-256 mismatch")
    dest.write_bytes(data)
    print(f"Saved {dest} ({len(data):,} bytes)")


def u32(blob: bytes, off: int) -> int:
    return struct.unpack_from("<I", blob, off)[0]


# ---------------------------------------------------------------------------
# Raw-block PPMd decompression
# ---------------------------------------------------------------------------


def decompress_block(data: bytes) -> bytes:
    """Decompress a raw PPMd block: [4 params][4 size][compressed data]."""
    order, mem = data[1], data[0] * 1024 * 1024
    size_field = u32(data, 4)
    payload = data[8 : 8 + (size_field & 0x7FFFFFFF)]
    if size_field & 0x80000000:  # stored
        return payload
    return pyppmd.Ppmd8gDecoder(order, mem).decode(payload, 16 << 20)


# ---------------------------------------------------------------------------
# GEA archive parsing & extraction
# ---------------------------------------------------------------------------


def parse_info_entries(data: bytes) -> list[tuple[str | None, int]]:
    """Parse GEA info block → list of (filename, packed_size)."""
    count = struct.unpack_from("<H", data, 0x0A)[0]
    entries, pos = [], 0x0D  # 0x0D-byte header

    for _ in range(count):
        if pos + 6 > len(data):
            break
        entry_size = struct.unpack_from("<H", data, pos)[0]
        packed_size = u32(data, pos + 2)
        # Scan tagged fields for the filename (tag 0x04)
        name, p = None, pos + 6
        while p < pos + entry_size:
            tag = data[p]
            if tag == 0x01:
                p += 13
            elif tag == 0x02:
                p += 9
            elif tag == 0x03:
                p += 5
            elif tag == 0x04:
                end = data.index(0, p + 1)
                name = data[p + 1 : end].decode("ascii", errors="replace")
                break
            else:
                break
        entries.append((name, packed_size))
        pos += entry_size

    return entries


def extract_gea(blob: bytes, gea_offset: int, output_dir: Path) -> list[Path]:
    """Extract all files from the GEA archive at *gea_offset*."""
    # Parse GEA header
    info_stored = u32(blob, gea_offset + 0x23)
    raw_info_sz = u32(blob, gea_offset + 0x13)
    total_size = u32(blob, gea_offset + 0x0C)
    data_offset = gea_offset + 0x27 + info_stored

    # Decompress the info block (sits right after the 0x27-byte header)
    info_src = blob[gea_offset + 0x1F : gea_offset + 0x27 + info_stored]
    entries = parse_info_entries(decompress_block(info_src))
    print(f"Archive: {len(entries)} files\n")

    # File data region: skip first sub-block, then read 4-byte params
    file_data = blob[data_offset + raw_info_sz : gea_offset + total_size]
    order, mem = file_data[1], file_data[0] * 1024 * 1024
    flags = file_data[3]

    dec = pyppmd.Ppmd8gDecoder(order, mem)
    pos, file_num, was_stored = 4, 0, False
    extracted: list[Path] = []

    for name, packed_size in entries:
        size_field = u32(file_data, pos)
        is_stored = bool(size_field & 0x80000000)
        chunk_len = size_field & 0x7FFFFFFF
        chunk = file_data[pos + 4 : pos + 4 + chunk_len]
        pos += 4 + chunk_len

        # Reset decoder between files
        if file_num > 0:
            if (flags & 1) and not was_stored:
                dec.lightweight_reset()
            else:
                dec.reinit(order)
        file_num += 1

        if is_stored:
            was_stored = True
            out = chunk
        else:
            was_stored = False
            out = dec.decode(chunk, max(packed_size * 2, 1 << 20)) if chunk_len else b""

        if not name:
            continue
        out_path = output_dir / Path(name.replace("\\", "/"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(out)
        extracted.append(out_path)
        mode = "stored" if is_stored else "ppmd"
        print(f"  {name}  ({len(out):,} bytes, {mode})")

    return extracted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else Path("stardef_extracted")
    exe_path = None
    if "--exe" in sys.argv:
        exe_path = Path(sys.argv[sys.argv.index("--exe") + 1])

    if exe_path is None:
        exe_path = output_dir / "stardef.exe"
        download(STARDEF_URL, exe_path, STARDEF_SHA256)

    blob = exe_path.read_bytes()
    gea_offset = u32(blob, 0x2800)  # overlay_end from stub header

    if blob[gea_offset : gea_offset + 4] != b"GEA\x00":
        sys.exit(f"No GEA archive at offset 0x{gea_offset:x}")

    output_dir.mkdir(parents=True, exist_ok=True)
    extracted = extract_gea(blob, gea_offset, output_dir)
    print(f"\nDone — {len(extracted)} files extracted to {output_dir}/")


if __name__ == "__main__":
    main()
