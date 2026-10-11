"""BPS patches from tools/mod/bps.py. Run: python3 -m unittest discover mod/tests"""

import random
import struct
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "mod"))

import bps  # noqa: E402


def finish(body: bytes, source: bytes, target: bytes) -> bytes:
    """Adds the three checksums to a hand-written patch."""
    out = body + struct.pack("<II", zlib.crc32(source), zlib.crc32(target))
    return out + struct.pack("<I", zlib.crc32(out))


class NumberTest(unittest.TestCase):
    # From the format's definition: each byte carries seven bits, low bits first, the
    # last byte has its top bit set, and every continuation adds one so that no value
    # has two encodings.
    KNOWN = {0: "80", 1: "81", 127: "ff", 128: "0080", 129: "0180", 16511: "7fff", 16512: "000080"}

    def test_known_encodings(self):
        for value, encoded in self.KNOWN.items():
            self.assertEqual(bps.encode_number(value).hex(), encoded, value)

    def test_known_decodings(self):
        for value, encoded in self.KNOWN.items():
            data = bytes.fromhex(encoded) + b"\x55"
            self.assertEqual(bps.decode_number(data, 0), (value, len(data) - 1), value)

    def test_round_trip(self):
        for value in list(range(0, 70000, 37)) + [0x4000000, 2**32 - 1, 2**40]:
            encoded = bps.encode_number(value)
            self.assertEqual(bps.decode_number(encoded, 0), (value, len(encoded)))

    def test_truncated_number(self):
        with self.assertRaises(bps.PatchError):
            bps.decode_number(bytes.fromhex("0000"), 0)


class CreateTest(unittest.TestCase):
    def test_exact_bytes_of_a_small_patch(self):
        source, target = b"ABCDEFGH", b"ABCDxFGH"
        # sizes 8 and 8, no metadata; read 4 from source, 1 from the patch, 3 from source
        body = b"BPS1" + bytes.fromhex("88 88 80") + bytes.fromhex("8c") + bytes.fromhex("81") + b"x" + bytes.fromhex("88")
        self.assertEqual(bps.create(source, target), finish(body, source, target))

    def test_identical_files(self):
        data = bytes(range(256)) * 40
        patch = bps.create(data, data)
        self.assertLess(len(patch), 32)
        self.assertEqual(bps.apply(data, patch), data)

    def test_round_trips(self):
        rng = random.Random(1)
        source = bytes(rng.randrange(256) for _ in range(3 * bps.BLOCK + 123))
        cases = {
            "one byte": lambda t: t.__setitem__(5000, t[5000] ^ 0xFF),
            "first and last": lambda t: (t.__setitem__(0, t[0] ^ 1), t.__setitem__(len(t) - 1, t[-1] ^ 1)),
            "across a block edge": lambda t: t.__setitem__(slice(bps.BLOCK - 3, bps.BLOCK + 3), b"\0" * 6),
            "near neighbours": lambda t: (t.__setitem__(100, t[100] ^ 1), t.__setitem__(102, t[102] ^ 1),
                                          t.__setitem__(200, t[200] ^ 1)),
            "longer": lambda t: t.extend(b"appended" * 100),
            "shorter": lambda t: t.__delitem__(slice(1000, None)),
            "empty": lambda t: t.clear(),
        }
        for name, change in cases.items():
            target = bytearray(source)
            change(target)
            patch = bps.create(source, bytes(target))
            self.assertEqual(bps.apply(source, patch), bytes(target), name)

    def test_patch_is_small_for_small_changes(self):
        source = bytes(1 << 20)
        target = bytearray(source)
        target[0x1234:0x1238] = b"\x12\x34\x56\x78"
        target[0x80000:0x80100] = bytes(range(256))
        self.assertLess(len(bps.create(source, bytes(target))), 300)

    def test_close_changes_share_one_run(self):
        source = bytes(64)
        target = bytearray(source)
        target[10] = target[12] = 1
        self.assertEqual(bps.differing_runs(source, bytes(target)), [(10, 13)])
        target[40] = 1
        self.assertEqual(bps.differing_runs(source, bytes(target)), [(10, 13), (40, 41)])


class ApplyTest(unittest.TestCase):
    def test_copy_actions(self):
        # Patches from other tools use all four actions. Output "HELLOHELLOaaaaa":
        #   SourceCopy 5 from offset 3, SourceCopy 5 stepping back 5,
        #   TargetRead "a", TargetCopy 4 from output offset 10 (overlapping itself).
        source = b"xyzHELLO"
        target = b"HELLOHELLOaaaaa"
        body = (b"BPS1" + bps.encode_number(len(source)) + bps.encode_number(len(target)) + bps.encode_number(0)
                + bps.encode_number((4 << 2) | bps.SOURCE_COPY) + bps.encode_number(3 << 1)
                + bps.encode_number((4 << 2) | bps.SOURCE_COPY) + bps.encode_number((5 << 1) | 1)
                + bps.encode_number((0 << 2) | bps.TARGET_READ) + b"a"
                + bps.encode_number((3 << 2) | bps.TARGET_COPY) + bps.encode_number(10 << 1))
        self.assertEqual(bps.apply(source, finish(body, source, target)), target)

    def test_metadata_is_skipped(self):
        source, target = b"abcd", b"abcd"
        note = b"<note/>"
        body = (b"BPS1" + bytes.fromhex("84 84") + bps.encode_number(len(note)) + note
                + bps.encode_number((3 << 2) | bps.SOURCE_READ))
        patch = finish(body, source, target)
        self.assertEqual(bps.apply(source, patch), target)
        self.assertEqual(bps.read_header(patch)["metadata"], note)

    def test_wrong_rom_is_refused(self):
        patch = bps.create(b"original", b"modified")
        with self.assertRaisesRegex(bps.PatchError, "different ROM"):
            bps.apply(b"0riginal", patch)
        with self.assertRaisesRegex(bps.PatchError, "different ROM"):
            bps.apply(b"original!", patch)

    def test_damaged_patch_is_refused(self):
        patch = bytearray(bps.create(b"original", b"modified"))
        patch[8] ^= 0x01
        with self.assertRaisesRegex(bps.PatchError, "damaged"):
            bps.apply(b"original", bytes(patch))

    def test_not_a_patch(self):
        for data in (b"", b"PATCH" + bytes(20), b"BPS1"):
            with self.assertRaisesRegex(bps.PatchError, "not a BPS patch"):
                bps.apply(b"original", data)

    def test_bad_actions_are_refused(self):
        source, target = b"abcd", b"abcdabcd"
        header = b"BPS1" + bytes.fromhex("84 88 80")
        bad = {
            "reads past the source": bps.encode_number((7 << 2) | bps.SOURCE_READ),
            "writes past the output": bps.encode_number((8 << 2) | bps.TARGET_READ) + b"abcdabcda",
            "data cut short": bps.encode_number((7 << 2) | bps.TARGET_READ) + b"abc",
            "copies from before the source": (bps.encode_number((3 << 2) | bps.SOURCE_COPY)
                                              + bps.encode_number((1 << 1) | 1)),
            "copies unwritten output": bps.encode_number((3 << 2) | bps.TARGET_COPY) + bps.encode_number(0),
            "wrong result": bps.encode_number((3 << 2) | bps.SOURCE_READ) + bps.encode_number((3 << 2) | bps.TARGET_READ) + b"abcX",
            "short result": bps.encode_number((3 << 2) | bps.SOURCE_READ),
        }
        for name, actions in bad.items():
            with self.assertRaises(bps.PatchError, msg=name):
                bps.apply(source, finish(header + actions, source, target))


if __name__ == "__main__":
    unittest.main()
