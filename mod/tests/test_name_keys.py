"""The nickname keyboard's key table. Run: python3 -m unittest discover mod/tests"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import gen_name_keys as gen  # noqa: E402

ROM = REPO_ROOT / "baseroms" / "us" / "baserom.z64"

# The nickname screens of the Game Boy games, from the pret disassemblies:
# pokecrystal data/text/name_input_chars.asm (NameInputUpper, NameInputLower) and
# pokered data/text/alphabets.asm. <PK>, <MN>, <DOT> are single tiles; <ED> ends entry.
CRYSTAL = ["A B C D E F G H I", "J K L M N O P Q R", "S T U V W X Y Z  ", "- ? ! / . ,      ",
           "a b c d e f g h i", "j k l m n o p q r", "s t u v w x y z  ", "× ( ) : ; [ ] <PK> <MN>"]
RED = ["ABCDEFGHI", "JKLMNOPQR", "STUVWXYZ ", "×():;[]<PK><MN>", "-?!♂♀/<DOT>,<ED>",
       "abcdefghi", "jklmnopqr", "stuvwxyz "]

# The game's English table from Game Boy codes to its own (D_80097380), in the ROM.
GB_TABLE = 0x80097380 - 0x80000400 + 0x1000
UNKNOWN = 0x80


def cartridge_keys(rows: list) -> set:
    keys = set()
    for row in rows:
        row = row.replace("<PK>", "\x01").replace("<MN>", "\x02").replace("<DOT>", ".").replace("<ED>", "")
        keys.update(row)
    return {{"\x01": "{PK}", "\x02": "{MN}"}.get(key, key) for key in keys}


class NameKeysTest(unittest.TestCase):
    def setUp(self):
        self.pages = gen.pages()
        self.keys = {key for page in self.pages for row in page for key in row}

    def test_shape(self):
        self.assertEqual(len(self.pages), 2)
        for page in self.pages:
            self.assertEqual([len(row) for row in page], [9, 9, 9, 9])

    def test_offers_exactly_what_the_cartridges_can_type(self):
        self.assertEqual(self.keys, cartridge_keys(CRYSTAL) | cartridge_keys(RED))

    def test_follows_the_crystal_layout(self):
        upper, lower = self.pages
        crystal = [row.replace("<PK>", "P").replace("<MN>", "M")[::2] for row in CRYSTAL]
        ours = ["".join({"{PK}": "P", "{MN}": "M"}.get(key, key) for key in row) for row in upper + lower]
        self.assertEqual(ours[:3], crystal[:3])
        self.assertEqual(ours[4:], crystal[4:])
        # Crystal's symbol row, then the two signs Red adds, in the cells Crystal leaves empty.
        self.assertEqual(ours[3], "-?!/.,♂♀ ")
        self.assertEqual(crystal[3], "-?!/.,   ")

    def test_no_key_appears_twice(self):
        for page in self.pages:
            keys = [key for row in page for key in row if key != " "]
            self.assertEqual(len(keys), len(set(keys)))

    def test_codes_are_distinct_and_cannot_be_mistaken(self):
        codes = [gen.KEYS[key][0] for key in self.keys]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertNotIn(0, codes)            # ends a name
        self.assertNotIn(ord("%"), codes)     # the game draws text through printf
        self.assertNotIn(UNKNOWN, codes)
        gb_codes = [gen.KEYS[key][1] for key in self.keys]
        self.assertEqual(len(gb_codes), len(set(gb_codes)))
        self.assertNotIn(0x50, gb_codes)      # ends a Game Boy name

    def test_split_row(self):
        self.assertEqual(gen.split_row("a{PK}b{MN}"), ["a", "{PK}", "b", "{MN}"])

    def test_checked_in_table_is_current(self):
        self.assertTrue(gen.DEFAULT_OUT.exists(), "run tools/mod/gen_name_keys.py")
        self.assertEqual(gen.DEFAULT_OUT.read_text(encoding="ascii"), gen.render())

    @unittest.skipUnless(ROM.exists(), "no base ROM")
    def test_every_key_survives_the_games_conversion(self):
        table = ROM.read_bytes()[GB_TABLE:GB_TABLE + 0x100]
        for key in sorted(self.keys):
            code, gb_code, _ = gen.KEYS[key]
            self.assertEqual(table[gb_code], code, key)
            # Saving looks a character up by scanning the table from the start, so the
            # first Game Boy code that gives this character must be the right one.
            self.assertEqual(table.index(code), gb_code, key)


if __name__ == "__main__":
    unittest.main()
