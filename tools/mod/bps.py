#!/usr/bin/env python3
"""Create and apply BPS patches, the format the mod is released in.

A patch holds only the bytes that differ from the original ROM, plus checksums of the
ROM it applies to and of the result, so it can be shared where the ROM cannot.

    tools/mod/bps.py create <original.z64> <modified.z64> <out.bps>
    tools/mod/bps.py apply  <original rom> <patch.bps> <out.z64>
    tools/mod/bps.py info   <patch.bps>

`apply` accepts .z64, .v64 and .n64 dumps and always writes .z64. Any other BPS patcher
(Floating IPS, Rom Patcher JS) can apply the patch too, given a .z64 ROM.

Format: "BPS1", then source size, target size and metadata size as variable-length
numbers, the metadata, a list of actions, and three little-endian CRC32s (source,
target, and the patch up to that point). Each action copies a run of bytes to the
output: from the same place in the source, from the patch itself, or from anywhere in
the source or in the output so far. Standard library only.
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path

from check_rom import to_z64

MAGIC = b"BPS1"
FOOTER_SIZE = 12

SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY = range(4)

# Compared a block at a time; only blocks that differ are walked byte by byte.
BLOCK = 0x1000
# An unchanged run this short costs more as its own action than as patch data.
MIN_SOURCE_RUN = 4


class PatchError(ValueError):
    pass


def encode_number(value: int) -> bytes:
    out = bytearray()
    while True:
        low = value & 0x7F
        value >>= 7
        if value == 0:
            out.append(0x80 | low)
            return bytes(out)
        out.append(low)
        value -= 1


def decode_number(data: bytes, at: int) -> tuple:
    """The number starting at `at`, and the offset just past it."""
    value, shift = 0, 1
    while True:
        if at >= len(data):
            raise PatchError("patch ends inside a number")
        byte = data[at]
        at += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, at
        shift <<= 7
        value += shift


def differing_runs(source: bytes, target: bytes) -> list:
    """Half-open ranges of `target` that cannot be read from the same offset of `source`."""
    runs = []
    common = min(len(source), len(target))
    start = None
    for block in range(0, common, BLOCK):
        end = min(block + BLOCK, common)
        if source[block:end] == target[block:end]:
            if start is not None:
                runs.append((start, block))
                start = None
            continue
        for i in range(block, end):
            if source[i] != target[i]:
                if start is None:
                    start = i
            elif start is not None:
                runs.append((start, i))
                start = None
    if start is not None:
        runs.append((start, common))
    if len(target) > common:
        runs.append((common, len(target)))

    merged = []
    for run in runs:
        if merged and run[0] - merged[-1][1] < MIN_SOURCE_RUN:
            merged[-1] = (merged[-1][0], run[1])
        else:
            merged.append(run)
    return merged


def create(source: bytes, target: bytes, metadata: bytes = b"") -> bytes:
    """A patch that turns `source` into `target`. Bytes are matched in place only, which
    suits a ROM where nothing moves."""
    out = bytearray(MAGIC)
    out += encode_number(len(source)) + encode_number(len(target))
    out += encode_number(len(metadata)) + metadata

    def action(kind: int, length: int) -> None:
        out.extend(encode_number(((length - 1) << 2) | kind))

    position = 0
    for start, end in differing_runs(source, target):
        if start > position:
            action(SOURCE_READ, start - position)
        action(TARGET_READ, end - start)
        out.extend(target[start:end])
        position = end
    if len(target) > position:
        action(SOURCE_READ, len(target) - position)

    out += struct.pack("<II", zlib.crc32(source), zlib.crc32(target))
    out += struct.pack("<I", zlib.crc32(out))
    return bytes(out)


def read_header(patch: bytes) -> dict:
    if len(patch) < len(MAGIC) + 3 + FOOTER_SIZE or patch[:4] != MAGIC:
        raise PatchError("not a BPS patch")
    source_crc, target_crc, patch_crc = struct.unpack_from("<III", patch, len(patch) - FOOTER_SIZE)
    if zlib.crc32(patch[:-4]) != patch_crc:
        raise PatchError("the patch file is damaged (its own checksum does not match)")
    at = len(MAGIC)
    source_size, at = decode_number(patch, at)
    target_size, at = decode_number(patch, at)
    metadata_size, at = decode_number(patch, at)
    if at + metadata_size > len(patch) - FOOTER_SIZE:
        raise PatchError("metadata runs past the end of the patch")
    return {"source_size": source_size, "target_size": target_size,
            "metadata": patch[at:at + metadata_size], "actions": at + metadata_size,
            "source_crc": source_crc, "target_crc": target_crc, "patch_crc": patch_crc}


def apply(source: bytes, patch: bytes) -> bytes:
    header = read_header(patch)
    if len(source) != header["source_size"] or zlib.crc32(source) != header["source_crc"]:
        raise PatchError(f"this patch is for a different ROM: expected {header['source_size']:#x} bytes "
                         f"with CRC32 {header['source_crc']:08x}, got {len(source):#x} bytes "
                         f"with CRC32 {zlib.crc32(source):08x}")

    target = bytearray()
    size = header["target_size"]
    at = header["actions"]
    end = len(patch) - FOOTER_SIZE
    source_at = target_at = 0
    while at < end:
        data, at = decode_number(patch, at)
        kind, length = data & 3, (data >> 2) + 1
        if len(target) + length > size:
            raise PatchError("patch writes past the end of its output")
        if kind == SOURCE_READ:
            start = len(target)
            if start + length > len(source):
                raise PatchError("patch reads past the end of the ROM")
            target += source[start:start + length]
        elif kind == TARGET_READ:
            if at + length > end:
                raise PatchError("patch data is cut short")
            target += patch[at:at + length]
            at += length
        else:
            data, at = decode_number(patch, at)
            step = -(data >> 1) if data & 1 else data >> 1
            if kind == SOURCE_COPY:
                source_at += step
                if source_at < 0 or source_at + length > len(source):
                    raise PatchError("patch copies from outside the ROM")
                target += source[source_at:source_at + length]
                source_at += length
            else:
                target_at += step
                if target_at < 0 or target_at >= len(target):
                    raise PatchError("patch copies from output it has not written yet")
                # May overlap what it is writing, which is how a repeated byte is stored.
                for _ in range(length):
                    target.append(target[target_at])
                    target_at += 1

    if len(target) != size or zlib.crc32(target) != header["target_crc"]:
        raise PatchError("the patched ROM does not match the patch's checksum")
    return bytes(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create", help="write the patch that turns one ROM into another")
    p.add_argument("source", type=Path)
    p.add_argument("target", type=Path)
    p.add_argument("patch", type=Path)
    p = sub.add_parser("apply", help="patch a ROM")
    p.add_argument("source", type=Path)
    p.add_argument("patch", type=Path)
    p.add_argument("target", type=Path)
    p = sub.add_parser("info", help="show what a patch expects and produces")
    p.add_argument("patch", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "create":
            source, target = args.source.read_bytes(), args.target.read_bytes()
            patch = create(source, target)
            if apply(source, patch) != target:
                raise PatchError("the new patch does not reproduce its target")
            args.patch.write_bytes(patch)
            print(f"wrote {args.patch}: {len(patch)} bytes")
        elif args.command == "apply":
            patch = args.patch.read_bytes()
            args.target.write_bytes(apply(to_z64(args.source.read_bytes()), patch))
            print(f"wrote {args.target}")
            return 0
        else:
            patch = args.patch.read_bytes()
        header = read_header(patch)
        print(f"applies to: {header['source_size']:#x} bytes, CRC32 {header['source_crc']:08x}")
        print(f"produces:   {header['target_size']:#x} bytes, CRC32 {header['target_crc']:08x}")
        if header["metadata"]:
            print(f"metadata:   {header['metadata'].decode('utf-8', 'replace')}")
    except (PatchError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
