"""The move clauses' data and the mod's rule set. Run: python3 -m unittest discover mod/tests

The moves are held against Pokemon Showdown's data, which needs the pinned copy in
mod/data/cache (tools/mod/gen_legal_moves.py --fetch); the rule set against the game's
own records, which needs the original ROM.
"""

import re
import struct
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import gen_legal_moves as gen  # noqa: E402

MOVES_FILE = gen.cache_path(gen.DEFAULT_CACHE, "moves")
CLAUSE_MOVES = REPO_ROOT / "mod" / "data" / "clause_moves.inc.c"
CLAUSES_HEADER = REPO_ROOT / "mod" / "include" / "clauses.h"
CLAUSES_SOURCE = REPO_ROOT / "mod" / "src" / "clauses.c"
RULE_SET = REPO_ROOT / "mod" / "data" / "rule_ou.inc.c"
BASE_ROM = REPO_ROOT / "baseroms" / "us" / "baserom.z64"

MAIN_ROM, MAIN_VRAM = 0x1000, 0x80000400
ANYTHING_GOES, POKE_CUP = 0x8009F5C4, 0x8009F64C   # the game's records of two rule sets
RULES_SIZE = 0x44
TEXT_ARCHIVE = 0x1D70000                           # the ROM's texts, a bank per directory entry
MOVE_NAMES = 6


def lists() -> dict:
    """The file's lists: name -> [(move id, the name in its comment)]."""
    text = CLAUSE_MOVES.read_text(encoding="ascii")
    found = {}
    for name, body in re.findall(r"static const u8 (\w+)\[\] = \{(.*?)\};", text, re.S):
        found[name] = [(int(number), comment) for number, comment in re.findall(r"(\d+), /\* (.*?) \*/", body)]
    return found


def baton_pass() -> int:
    return int(re.search(r"#define MOVE_BATON_PASS (\d+)", CLAUSE_MOVES.read_text(encoding="ascii")).group(1))


def showdown() -> dict:
    """Move number -> (name, what the entry says), for the moves of the first two generations."""
    moves = {}
    for _, lines in gen.iter_entries(MOVES_FILE):
        body = "\n".join(lines)
        number = int(re.search(r"^\t\tnum: (-?\d+),", body, re.M).group(1))
        if 1 <= number <= gen.NUM_MOVES:
            moves[number] = (re.search(r'^\t\tname: "(.*?)",', body, re.M).group(1), body)
    return moves


class ClauseListsTest(unittest.TestCase):
    def test_the_file_has_the_three_lists(self):
        found = lists()
        self.assertEqual(sorted(found), ["sEvasionMoves", "sOhkoMoves", "sTrappingMoves"])
        for name, moves in found.items():
            numbers = [number for number, _ in moves]
            self.assertEqual(numbers, sorted(set(numbers)), name)

    def test_the_clauses_are_the_low_bits_of_the_flags(self):
        header = CLAUSES_HEADER.read_text(encoding="ascii")
        bits = {name: int(value, 16) for name, value in re.findall(r"#define CLAUSE_(\w+) (0x[0-9A-Fa-f]+)", header)}
        self.assertEqual(bits, {"EVASION": 1, "OHKO": 2, "TRAP_PASS": 4, "MASK": 7})


@unittest.skipUnless(MOVES_FILE.exists(), "source data not cached; run gen_legal_moves.py --fetch")
class ShowdownTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.moves = showdown()

    def numbers(self, wanted) -> list:
        return sorted(number for number, (_, body) in self.moves.items() if wanted(body))

    def test_each_move_is_the_one_its_comment_names(self):
        self.assertEqual(len(self.moves), gen.NUM_MOVES)
        for name, moves in lists().items():
            for number, comment in moves:
                self.assertEqual(self.moves[number][0], comment, name)
        self.assertEqual(self.moves[baton_pass()][0], "Baton Pass")

    def test_evasion_moves_are_those_that_raise_the_users_evasion(self):
        raises = re.compile(r'^\t\tboosts: \{\n\t\t\tevasion: [1-9]', re.M)
        found = self.numbers(lambda body: raises.search(body) and '\t\ttarget: "self",' in body)
        self.assertEqual([number for number, _ in lists()["sEvasionMoves"]], found)
        self.assertEqual([self.moves[number][0] for number in found], ["Double Team", "Minimize"])

    def test_ohko_moves_are_those_that_knock_out_in_one_hit(self):
        found = self.numbers(lambda body: re.search(r"^\t\tohko: ", body, re.M))
        self.assertEqual([number for number, _ in lists()["sOhkoMoves"]], found)
        self.assertEqual([self.moves[number][0] for number in found], ["Guillotine", "Horn Drill", "Fissure"])

    def test_trapping_moves_are_those_that_keep_the_foe_from_switching(self):
        found = self.numbers(lambda body: "addVolatile('trapped'" in body)
        self.assertEqual([number for number, _ in lists()["sTrappingMoves"]], found)
        self.assertEqual([self.moves[number][0] for number in found], ["Spider Web", "Mean Look"])


@unittest.skipUnless(BASE_ROM.exists(), "no original ROM")
class RomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = BASE_ROM.read_bytes()

    def record(self, address: int) -> bytes:
        at = address - MAIN_VRAM + MAIN_ROM
        return self.rom[at:at + RULES_SIZE]

    def test_the_viewer_names_the_moves_as_the_game_does(self):
        # The game's names for the moves are a bank of its texts, in the moves' order.
        offset, size = struct.unpack_from(">II", self.rom, TEXT_ARCHIVE + 0x10 + MOVE_NAMES * 0x10)
        bank = self.rom[TEXT_ARCHIVE + offset:TEXT_ARCHIVE + offset + size]
        count, = struct.unpack_from(">I", bank, 0)
        starts = struct.unpack_from(f">{count}I", bank, 4)

        def name(move: int) -> str:
            start = starts[move - 1]
            return bank[start:bank.index(b"\0", start)].decode("ascii")

        sentences = dict(re.findall(r'static char (s\w+)\[\] = "(.*?)";', CLAUSES_SOURCE.read_text(encoding="ascii")))
        found = lists()
        for sentence, moves in (("sEvasion", found["sEvasionMoves"]), ("sOhko", found["sOhkoMoves"]),
                                ("sTrapPass", found["sTrappingMoves"] + [(baton_pass(), "Baton Pass")])):
            text = sentences[sentence].replace("\\n", " ")
            named = set(re.findall(r"[A-Z]{2,}(?: [A-Z]{2,})*", text.replace("POK\\xE9MON", "")))
            self.assertEqual(named, {name(move) for move, _ in moves}, sentence)

    def test_the_rule_set_is_anything_goes_without_the_poke_cups_five(self):
        text = RULE_SET.read_text(encoding="ascii")
        body = text[text.index("static Rules sOuRules"):]
        name = re.search(r'^\s*"(.*?)",', body, re.M).group(1)
        species = bytes(int(value, 16) for value in re.findall(r"0x([0-9A-F]{2})\b", body[:body.index("RULES_ANYTHING_GOES")]))
        rest = re.sub(r"/\*.*?\*/", "", body[body.index("RULES_ANYTHING_GOES"):], flags=re.S)
        kind, lowest, highest, total, background, rentals, name_text, flags = [
            field.strip() for field in rest.split("};")[0].split(",") if field.strip()]

        stock, cup = self.record(ANYTHING_GOES), self.record(POKE_CUP)
        self.assertLess(len(name), 0x14)
        self.assertEqual(species, cup[0x14:0x34])
        banned = [index + 1 for index in range(251) if not species[index >> 3] & (0x80 >> (index & 7))]
        self.assertEqual(banned, [150, 151, 249, 250, 251])   # Mewtwo, Mew, Lugia, Ho-Oh, Celebi
        self.assertEqual(kind, "RULES_ANYTHING_GOES")
        self.assertEqual(struct.unpack_from(">h", stock, 0x34)[0], 5)
        self.assertEqual((int(lowest), int(highest)), (stock[0x36], stock[0x37]))
        self.assertEqual((int(total), int(background), int(rentals)), struct.unpack_from(">Hhh", stock, 0x38))
        self.assertEqual(int(name_text), -1)
        stock_flags, = struct.unpack_from(">I", stock, 0x40)
        self.assertEqual(flags, f"0x{stock_flags:08X} | CLAUSE_EVASION | CLAUSE_OHKO | CLAUSE_TRAP_PASS")

    def test_no_rule_set_of_the_games_uses_the_clauses_bits(self):
        # Fourteen records, one after the other, each found by its kind.
        table = 0x8009F828 - MAIN_VRAM + MAIN_ROM
        for kind, address in enumerate(struct.unpack_from(">14I", self.rom, table)):
            record = self.record(address)
            self.assertEqual(struct.unpack_from(">h", record, 0x34)[0], kind)
            self.assertEqual(struct.unpack_from(">I", record, 0x40)[0] & 0xFFFF, 0, kind)


if __name__ == "__main__":
    unittest.main()
