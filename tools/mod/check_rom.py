#!/usr/bin/env python3
"""Validate a Pokemon Stadium 2 (US) ROM and install it as baseroms/us/baserom.z64.

Accepts .z64 (big-endian), .v64 (byte-swapped) or .n64 (little-endian) dumps and
converts to .z64 before hashing. Standard library only.

    tools/mod/check_rom.py <path-to-rom>          # verify + install
    tools/mod/check_rom.py --verify-only <path>   # verify, write nothing
"""

import argparse
import hashlib
import sys
from pathlib import Path

US_SHA1 = "d8343e69a7dc63b869cf6361d87cde64444281d3"
US_MD5 = "1561c75d11cedf356a8ddb1a4a5f9d5d"
ROM_SIZE = 0x4000000

MAGIC_Z64 = bytes.fromhex("80371240")
MAGIC_V64 = bytes.fromhex("37804012")
MAGIC_N64 = bytes.fromhex("40123780")

# Unused 0xFF padding the mod fragment is injected into (see mod/NOTES.md).
HOLE_START = 0x16061C0
HOLE_END = 0x1638000
# And the padding in front of the trainer pictures, where the mod puts a directory of
# them (see tools/mod/gen_trainer_faces.py).
PICTURES_START = 0x225A820
PICTURES_END = 0x2268000


def to_z64(data: bytes) -> bytes:
    magic = data[:4]
    if magic == MAGIC_Z64:
        return data
    if len(data) % 4:
        raise ValueError("ROM size is not a multiple of 4 bytes")
    out = bytearray(data)
    if magic == MAGIC_V64:
        out[0::2], out[1::2] = data[1::2], data[0::2]
        return bytes(out)
    if magic == MAGIC_N64:
        out[0::4], out[1::4], out[2::4], out[3::4] = data[3::4], data[2::4], data[1::4], data[0::4]
        return bytes(out)
    raise ValueError(f"not an N64 ROM (magic {magic.hex()})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rom", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--dest", type=Path,
                        default=Path(__file__).resolve().parents[2] / "baseroms" / "us" / "baserom.z64")
    args = parser.parse_args()

    raw = args.rom.read_bytes()
    try:
        rom = to_z64(raw)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    sha1 = hashlib.sha1(rom).hexdigest()
    md5 = hashlib.md5(rom).hexdigest()
    title = rom[0x20:0x34].decode("ascii", "replace").strip()
    code = rom[0x3B:0x3F].decode("ascii", "replace")
    print(f"title:   {title!r}  code: {code}  revision: {rom[0x3F]}")
    print(f"size:    {len(rom):#x}" + ("" if len(rom) == ROM_SIZE else f"  (expected {ROM_SIZE:#x})"))
    print(f"format:  {'z64' if raw[:4] == MAGIC_Z64 else 'converted to z64'}")
    print(f"sha1:    {sha1}")
    print(f"md5:     {md5}")

    if sha1 != US_SHA1:
        print(f"error: sha1 mismatch, expected {US_SHA1} (Pokemon Stadium 2, USA)", file=sys.stderr)
        return 1
    print("match:   Pokemon Stadium 2 (USA)")

    hole = rom[HOLE_START:HOLE_END]
    if hole.count(0xFF) == len(hole):
        print(f"hole:    {HOLE_START:#x}-{HOLE_END:#x} is all 0xFF ({len(hole)} bytes free)")
    else:
        used = len(hole) - hole.count(0xFF)
        print(f"hole:    WARNING {used} non-0xFF bytes in {HOLE_START:#x}-{HOLE_END:#x}")
    pad = rom[PICTURES_START:PICTURES_END]
    if pad.count(0xFF) == len(pad):
        print(f"         {PICTURES_START:#x}-{PICTURES_END:#x} is all 0xFF ({len(pad)} bytes free)")
    else:
        used = len(pad) - pad.count(0xFF)
        print(f"         WARNING {used} non-0xFF bytes in {PICTURES_START:#x}-{PICTURES_END:#x}")

    if not args.verify_only:
        args.dest.parent.mkdir(parents=True, exist_ok=True)
        args.dest.write_bytes(rom)
        print(f"wrote:   {args.dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
