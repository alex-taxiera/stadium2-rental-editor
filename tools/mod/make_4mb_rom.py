#!/usr/bin/env python3
"""Make a test copy of a ROM that runs as if the console had no Expansion Pak.

BizHawk's Ares64 core always emulates 8 MB of RAM. The game sizes its main memory pool
from osGetMemSize(), so making that function return 4 MB leaves the game with the pool
it has on a console without the pak. The copy is for testing only: start it from power
on, because savestates carry the pool they were made with.

    tools/mod/make_4mb_rom.py build/pokestadiumgs-us-mod.z64 .emu/remote/mod-4mb.z64

Needs ipl3checksum, so run it with the build's Python (~/.venvs/stadium2/bin/python3).
"""

import argparse
import struct
import sys
from pathlib import Path

from modtool import update_checksum

# osGetMemSize, in the main segment (ROM 0x1000 is loaded at 0x80000400).
OS_GET_MEM_SIZE = 0x8007A160 - 0x80000400 + 0x1000
STOCK = bytes.fromhex("27bdfff0 3c0e0040")           # addiu sp, sp, -0x10 ; lui t6, 0x40
RETURN_4MB = struct.pack(">III", 0x3C020040, 0x03E00008, 0)   # lui v0, 0x40 ; jr ra ; nop


def patch(rom: bytearray) -> None:
    if rom[OS_GET_MEM_SIZE:OS_GET_MEM_SIZE + len(STOCK)] != STOCK:
        raise ValueError("osGetMemSize is not where it is in the US ROM")
    rom[OS_GET_MEM_SIZE:OS_GET_MEM_SIZE + len(RETURN_4MB)] = RETURN_4MB
    update_checksum(rom)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rom", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()

    rom = bytearray(args.rom.read_bytes())
    try:
        patch(rom)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    args.out.write_bytes(rom)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
