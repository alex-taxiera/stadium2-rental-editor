"""Checks of what the editor draws, by hashing a rectangle of a screenshot.

Game memory says what the editor holds, but not what it painted. For that the tests
take a screenshot, hash the pixels of the editor's window, and compare the hash with one
recorded in screens.json. Only hashes are kept, not the screenshots.

A failing check leaves the screenshot in .emu/test/remote for a look. Recorded hashes
are replaced by running the tests with UPDATE_SCREENS=1, which is only right after
looking at the screens. Standard library only.
"""

import hashlib
import json
import os
import struct
import zlib
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "screens.json"
UPDATE = os.environ.get("UPDATE_SCREENS") == "1"

# The inside of the editor window in a 640x480 screenshot: EDIT_WINDOW_* in
# mod/include/edit.h, less the frame.
WINDOW = (56, 77, 583, 244)
# The inside of the ENTER menu box, where EDIT and the key hints go.
SIDEBAR = (456, 264, 584, 391)
# The inside of the trainer window (mod/src/trainer.c).
TRAINER = (118, 263, 519, 440)
# The team menu's entries, in the same place: the stock five and the mod's two.
TEAM_MENU = (212, 263, 425, 460)
# The inside of the box over the list that asks which of the team is meant.
TEAM_QUESTION = (190, 220, 448, 260)
# Player 1's picture where the two sides are set against each other before a battle,
# and the title and name under it.
VERSUS = (70, 60, 160, 150)
VERSUS_LABEL = (56, 178, 186, 234)
# The box in the detail panel that shows the Pokemon's 3D model.
MODEL = (80, 296, 138, 354)


def read_png(path: Path, last_row: int = None) -> tuple:
    """(width, height, bytes per pixel, rows) of an 8-bit RGB or RGBA PNG. Rows after
    `last_row` are not decoded."""
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")
    at, header, packed = 8, None, bytearray()
    while at < len(data):
        length, kind = struct.unpack_from(">I4s", data, at)
        body = data[at + 8:at + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            packed += body
        at += 12 + length
    width, height, depth, colour, _, _, interlace = header
    if depth != 8 or colour not in (2, 6) or interlace != 0:
        raise ValueError(f"{path}: only plain 8-bit RGB and RGBA images are supported")
    size = 3 if colour == 2 else 4
    stride = width * size
    raw = zlib.decompress(bytes(packed))

    rows = []
    previous = bytearray(stride)
    count = height if last_row is None else min(height, last_row + 1)
    for y in range(count):
        start = y * (stride + 1)
        kind = raw[start]
        row = bytearray(raw[start + 1:start + 1 + stride])
        if kind == 1:
            for i in range(size, stride):
                row[i] = (row[i] + row[i - size]) & 0xFF
        elif kind == 2:
            for i in range(stride):
                row[i] = (row[i] + previous[i]) & 0xFF
        elif kind == 3:
            for i in range(stride):
                left = row[i - size] if i >= size else 0
                row[i] = (row[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                left = row[i - size] if i >= size else 0
                up = previous[i]
                corner = previous[i - size] if i >= size else 0
                estimate = left + up - corner
                a, b, c = abs(estimate - left), abs(estimate - up), abs(estimate - corner)
                row[i] = (row[i] + (left if a <= b and a <= c else up if b <= c else corner)) & 0xFF
        elif kind != 0:
            raise ValueError(f"{path}: unknown filter {kind} on row {y}")
        rows.append(row)
        previous = row
    return width, height, size, rows


def region_hash(path: Path, box: tuple) -> str:
    """SHA-1 of the red, green and blue bytes inside box = (left, top, right, bottom)."""
    left, top, right, bottom = box
    width, height, size, rows = read_png(path, bottom - 1)
    if right > width or bottom > height:
        raise ValueError(f"{path} is {width}x{height}, too small for {box}")
    digest = hashlib.sha1()
    for y in range(top, bottom):
        row = rows[y]
        if size == 3:
            digest.update(row[left * 3:right * 3])
        else:
            for x in range(left, right):
                digest.update(row[x * 4:x * 4 + 3])
    return digest.hexdigest()


def region_mean(path: Path, box: tuple) -> tuple:
    """Average red, green and blue inside box, for checks that only ask whether a picture
    changed colour."""
    left, top, right, bottom = box
    _, _, size, rows = read_png(path, bottom - 1)
    totals = [0, 0, 0]
    for y in range(top, bottom):
        row = rows[y]
        for channel in range(3):
            totals[channel] += sum(row[left * size + channel:right * size:size])
    pixels = (right - left) * (bottom - top)
    return tuple(total / pixels for total in totals)


def recorded() -> dict:
    return json.loads(RECORD.read_text(encoding="ascii")) if RECORD.exists() else {}


def check(test, name: str, path: Path, box: tuple = WINDOW) -> None:
    """Fails `test` unless the region of the screenshot matches the hash recorded as `name`."""
    actual = region_hash(path, box)
    record = recorded()
    if UPDATE:
        record[name] = actual
        RECORD.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="ascii", newline="\n")
        return
    test.assertIn(name, record, f"no hash recorded for screen {name!r}; look at {path}, then run with UPDATE_SCREENS=1")
    test.assertEqual(actual, record[name], f"screen {name!r} changed; see {path}")
