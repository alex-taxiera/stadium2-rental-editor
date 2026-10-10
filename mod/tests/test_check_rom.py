"""Byte-order handling in tools/mod/check_rom.py. Run: python3 -m unittest discover mod/tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "mod"))

import check_rom  # noqa: E402


def swap16(data: bytes) -> bytes:
    out = bytearray(data)
    out[0::2], out[1::2] = data[1::2], data[0::2]
    return bytes(out)


def swap32(data: bytes) -> bytes:
    out = bytearray(data)
    out[0::4], out[1::4], out[2::4], out[3::4] = data[3::4], data[2::4], data[1::4], data[0::4]
    return bytes(out)


class ToZ64Test(unittest.TestCase):
    def setUp(self):
        self.z64 = check_rom.MAGIC_Z64 + bytes(range(1, 253))

    def test_z64_is_unchanged(self):
        self.assertEqual(check_rom.to_z64(self.z64), self.z64)

    def test_v64_is_byte_swapped_back(self):
        v64 = swap16(self.z64)
        self.assertEqual(v64[:4], check_rom.MAGIC_V64)
        self.assertEqual(check_rom.to_z64(v64), self.z64)

    def test_n64_is_word_swapped_back(self):
        n64 = swap32(self.z64)
        self.assertEqual(n64[:4], check_rom.MAGIC_N64)
        self.assertEqual(check_rom.to_z64(n64), self.z64)

    def test_unknown_magic_is_rejected(self):
        with self.assertRaises(ValueError):
            check_rom.to_z64(b"\x00\x01\x02\x03" + bytes(12))


if __name__ == "__main__":
    unittest.main()
