#!/usr/bin/env python3
"""Give every picture of the game's trainers a number of its own.

The trainer pictures are an archive in the ROM: a directory with an entry per trainer,
and at each entry's offset a block that says how many pictures the trainer has, one to
three, and where each one is. The game asks for (trainer, picture), and the stock code
the mod changed for a player's choice (mod/stock_patches.txt) has room for a trainer's
number only: it always asks for the first picture.

So the archive gets a second directory, in unused ROM space just in front of it. Its
first entries are the stock ones, and after them comes one more for every further
picture, each leading to a block of its own that names that one picture as a trainer's
first. A choice is then a number in this directory, and the changed code needs nothing
new. The game finds the archive through a table of addresses in the ROM, whose entry is
pointed at the new directory. No picture moves, and the stock trainers keep their
numbers and all their pictures.

Which of a trainer's pictures the window shows first is decided here too, by eye: the
game's own choice for its trainers is not in one place to be read. See DEFAULT_FACES.

    tools/mod/gen_trainer_faces.py     # writes mod/data/trainer_faces.inc.c

Standard library only.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_rom import PICTURES_END, PICTURES_START  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_ROM = REPO_ROOT / "baseroms" / "us" / "baserom.z64"
DEFAULT_OUT = REPO_ROOT / "mod" / "data" / "trainer_faces.inc.c"

STOCK_ROM = 0x02268000        # the archive: a header, the directory, then the trainers' blocks
ARCHIVE_TABLE = 0x437620      # where each of the game's archives starts, four bytes each
ARCHIVE_NUMBER = 0xF          # this one's place in it
# 0xFF padding between the end of the archive before this one and its start.
SLACK_START, SLACK_END = PICTURES_START, PICTURES_END
DIRECTORY_ROM = 0x0225B000    # the new directory, and after it the new blocks

HEADER_SIZE = ENTRY_SIZE = BLOCK_SIZE = 0x10
PICTURE_BYTES = 0x2008        # an 8-byte header and 64 x 64 pixels of two bytes
MAX_FACES = 3                 # the game reads a block's count and three places, no more

# The picture the window shows first for a trainer, where it is not the last one. With
# three, the game's go upset, pleased, composed, and with two mostly upset, composed, so
# the last is the one a trainer meets you with: CAL's third is what the game itself
# shows of him before a battle, and the player's own second. These are the trainers whose
# pictures do not run that way, or whose last is not the one that looks best, as chosen
# from a sheet of them all.
DEFAULT_FACES = {
    0x00: 1,   # pleased, composed, upset
    0x03: 1,   # the last has the cap over the eyes
    0x07: 0,   # pleased, upset
    0x16: 1,   # the last is mid-shout behind a fan
    0x21: 1,   # upset, composed, downcast
    0x22: 1,   # composed, pleased, upset
}


def table_entry() -> int:
    """Where in the ROM the archive's address is kept."""
    return ARCHIVE_TABLE + ARCHIVE_NUMBER * 4


def pictures(rom: bytes) -> list:
    """For each stock trainer, where in the ROM each of its pictures starts, header included."""
    count, = struct.unpack_from(">I", rom, STOCK_ROM + 0xC)
    trainers = []
    for trainer in range(count):
        offset, = struct.unpack_from(">I", rom, STOCK_ROM + HEADER_SIZE + trainer * ENTRY_SIZE)
        block = STOCK_ROM + offset
        faces, = struct.unpack_from(">I", rom, block)
        trainers.append([block + place - 8 for place in struct.unpack_from(f">{faces}I", rom, block + 4)])
    return trainers


def numbers(rom: bytes) -> list:
    """(trainer, face) for every number of the new directory: each trainer's first
    picture under the trainer's own number, then the others, trainer by trainer."""
    trainers = pictures(rom)
    return ([(trainer, 0) for trainer in range(len(trainers))]
            + [(trainer, face) for trainer, faces in enumerate(trainers) for face in range(1, len(faces))])


def number_of(rom: bytes, trainer: int, face: int) -> int:
    return numbers(rom).index((trainer, face))


def default_face(trainer: int, faces: int) -> int:
    return DEFAULT_FACES.get(trainer, faces - 1)


def directory(rom: bytes) -> bytes:
    """The new directory and its blocks, as they go into the ROM at DIRECTORY_ROM."""
    trainers = pictures(rom)
    flags, zero, size, count = struct.unpack_from(">4I", rom, STOCK_ROM)
    listed = numbers(rom)
    moved = STOCK_ROM - DIRECTORY_ROM
    blocks_at = DIRECTORY_ROM + HEADER_SIZE + len(listed) * ENTRY_SIZE

    image = bytearray(struct.pack(">4I", flags, zero, size + moved, len(listed)))
    blocks = bytearray()
    for number, (trainer, face) in enumerate(listed):
        if face == 0:
            entry = struct.unpack_from(">4I", rom, STOCK_ROM + HEADER_SIZE + number * ENTRY_SIZE)
            image += struct.pack(">4I", entry[0] + moved, *entry[1:])
            continue
        block = blocks_at + len(blocks)
        image += struct.pack(">4I", block - DIRECTORY_ROM, BLOCK_SIZE, 0, 0)
        blocks += struct.pack(">4I", 1, trainers[trainer][face] + 8 - block, 0, 0)
    return bytes(image + blocks)


def install(rom: bytearray) -> int:
    """Writes the new directory into the ROM and points the game at it. Returns how many
    numbers it has."""
    image = directory(rom)
    end = DIRECTORY_ROM + len(image)
    if not SLACK_START <= DIRECTORY_ROM < end <= SLACK_END == STOCK_ROM:
        raise ValueError(f"the trainer directory is {len(image):#x} bytes, more than fit before the archive")
    if rom[SLACK_START:SLACK_END].count(0xFF) != SLACK_END - SLACK_START:
        raise ValueError("the space before the trainer pictures is not empty; inject into an unmodified build")
    if struct.unpack_from(">I", rom, table_entry())[0] != STOCK_ROM:
        raise ValueError("the trainer pictures are not where the original ROM has them")
    rom[DIRECTORY_ROM:end] = image
    struct.pack_into(">I", rom, table_entry(), DIRECTORY_ROM)
    return struct.unpack_from(">I", image, 0xC)[0]


def render(rom: bytes) -> str:
    trainers = pictures(rom)
    listed = numbers(rom)
    lines = ["// Generated by tools/mod/gen_trainer_faces.py. Do not edit by hand.",
             "// For each of the game's trainers: how many pictures it has, the number its second",
             "// has in the directory the mod gives the archive (the first keeps the trainer's",
             "// own number, and a third follows the second), and which one the window shows first.",
             "static const u8 sTrainerFaces[][3] = {"]
    rows = []
    for trainer, faces in enumerate(trainers):
        second = listed.index((trainer, 1)) if len(faces) > 1 else 0
        rows.append(f"{{{len(faces)}, 0x{second:02X}, {default_face(trainer, len(faces))}}}")
    for start in range(0, len(rows), 6):
        lines.append("    " + ", ".join(rows[start:start + 6]) + ",")
    lines += ["};", ""]
    return "\n".join(lines)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.write_text(render(BASE_ROM.read_bytes()), encoding="ascii", newline="\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
