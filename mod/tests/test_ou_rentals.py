"""The rental Pokemon OU Rules gives in place of the game's own: Smogon's GSC OU sets, as
tools/mod/gen_ou_rentals.py writes them. Run: python3 -m unittest discover mod/tests

Needs the original ROM and the pinned source data in mod/data/cache
(tools/mod/gen_ou_rentals.py --fetch).
"""

import json
import re
import struct
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import gen_legal_moves as legal  # noqa: E402
import gen_ou_rentals as gen  # noqa: E402

OU_RENTALS = REPO_ROOT / "mod" / "data" / "rental_ou.inc.c"
RULE_SET = REPO_ROOT / "mod" / "data" / "rule_ou.inc.c"
RENTALS_SOURCE = REPO_ROOT / "mod" / "src" / "rentals.c"
RENTAL_ARCHIVE, RENTAL_SIZE, LEVEL_100 = 0x1708000, 0x18, 1
ARIADOS = 168

HAVE_DATA = (gen.BASE_ROM.exists()
             and all(gen.cache_path(gen.DEFAULT_CACHE, key).exists() for key in gen.SOURCES)
             and all(legal.cache_path(gen.DEFAULT_CACHE, key).exists() for key in legal.SOURCES))


def ou_rentals() -> list:
    """(the record as the compiler makes it, its comment) for each of the file's records."""
    text = OU_RENTALS.read_text(encoding="ascii")
    body = text[text.index("static Rental sOuRentals"):]
    found = []
    for comment, fields in re.findall(r"/\* (.*?) \*/\s*\{ (.*?) \},\n", body):
        level, species, item, unk, m1, m2, m3, m4, pp_ups, happiness, *rest = [
            int(number, 0) for number in re.findall(r"0x[0-9A-Fa-f]+|\d+", fields)]
        stat_exp, dvs, tail = rest[:5], rest[5], rest[6:]
        found.append((struct.pack(">10B5HH2B", level, species, item, unk, m1, m2, m3, m4, pp_ups, happiness,
                                  *stat_exp, dvs, *tail), comment))
    return found


def parse_comment(comment: str) -> tuple:
    """(species, [move names], item name, set name) of a record's comment."""
    m = re.fullmatch(r'(.+?): (.*) \((.*?); Smogon\'s "(.*)"\)', comment)
    return m.group(1), m.group(2).split(", "), m.group(3), m.group(4)


@unittest.skipUnless(HAVE_DATA, "no baserom, or source data not cached; run gen_ou_rentals.py --fetch")
class OuRentalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = gen.BASE_ROM.read_bytes()
        cls.generator = gen.Generator(gen.DEFAULT_CACHE, cls.rom)
        cls.records = ou_rentals()
        cls.sets = json.loads(gen.cache_path(gen.DEFAULT_CACHE, "sets").read_text(encoding="utf-8"))
        cls.names = gen.move_names(cls.rom)

    def test_the_file_is_what_the_generator_makes(self):
        self.generator.notes, self.generator.passed_over = [], []
        made = gen.render(self.generator, self.generator.records())
        self.assertEqual(made, OU_RENTALS.read_text(encoding="ascii"))
        self.assertIn(f"#define NUM_OU_RENTALS {len(self.records)}\n", made)

    def test_one_for_each_species_smogon_has_a_set_for(self):
        species = [record[1] for record, _ in self.records]
        self.assertEqual(species, sorted(set(species)))
        smogon = {self.generator.species(name) for name in self.sets}
        # All but Ariados, whose one set has Spider Web with Baton Pass, which OU Rules keeps out.
        self.assertEqual(smogon - set(species), {ARIADOS})
        self.assertEqual(set(species) - smogon, set())
        self.assertIn("keep the game's own: Ariados.", OU_RENTALS.read_text(encoding="ascii"))

    def test_each_is_one_the_game_rents_and_ou_rules_admits(self):
        at = RENTAL_ARCHIVE + struct.unpack_from(">I", self.rom, RENTAL_ARCHIVE + 0x10 + LEVEL_100 * 0x10)[0]
        stock = {self.rom[at + 4 + i * RENTAL_SIZE + 1] for i in range(self.rom[at])}
        text = RULE_SET.read_text(encoding="ascii")
        mask = [int(byte, 16) for byte in re.search(r'"OU Rules",\s*/\*.*?\*/\s*\{(.*?)\}', text, re.S)
                .group(1).replace("\n", " ").split(", ")]
        for record, _ in self.records:
            self.assertIn(record[1], stock)
            self.assertTrue(mask[(record[1] - 1) >> 3] & (0x80 >> ((record[1] - 1) & 7)), record[1])

    def test_each_move_can_be_known_and_no_clause_keeps_it_out(self):
        knowable = self.generator.legal
        refused, trapping, baton_pass = gen.clause_moves(gen.CLAUSE_MOVES)
        for record, comment in self.records:
            moves = [move for move in record[4:8] if move]
            self.assertEqual(len(moves), len(set(moves)), comment)
            self.assertEqual(list(record[4:8]), moves + [0] * (4 - len(moves)), comment)
            for move in moves:
                self.assertIn(move, knowable[record[1]], comment)
                self.assertNotIn(move, refused, comment)
            self.assertFalse(baton_pass in moves and trapping & set(moves), comment)

    def test_the_comments_name_the_moves_as_the_game_does(self):
        for record, comment in self.records:
            _, named, _, _ = parse_comment(comment)
            self.assertEqual([name.split(" [")[0] for name in named],
                             [self.names[move] for move in record[4:8] if move], comment)

    def test_hidden_power_is_of_the_type_its_comment_names_at_full_power(self):
        for record, comment in self.records:
            dvs, = struct.unpack_from(">H", record, 0x14)
            dvs = {"atk": dvs >> 12, "def": (dvs >> 8) & 15, "spe": (dvs >> 4) & 15, "spa": dvs & 15}
            _, named, _, _ = parse_comment(comment)
            typed = [name for name in named if " [" in name]
            if 237 in record[4:8]:   # Hidden Power
                self.assertEqual(len(typed), 1, comment)
                kind, power = gen.hidden_power(dvs)
                self.assertEqual(f"[{gen.HIDDEN_POWER_TYPES[kind]}]", typed[0].split(" ", 2)[-1], comment)
                self.assertEqual(power, 70, comment)
            else:
                self.assertEqual(typed, [], comment)
                self.assertEqual(dvs, dict.fromkeys(dvs, 15), comment)

    def test_each_item_is_the_one_named_and_the_list_offers_it_to_the_species(self):
        items = gen.parse_items(gen.cache_path(gen.DEFAULT_CACHE, "items"))
        for record, comment in self.records:
            _, _, item_name, _ = parse_comment(comment)
            if item_name == "no item":
                self.assertEqual(record[2], 0, comment)
                continue
            self.assertEqual(record[2], items[legal.to_id(item_name)], comment)
            self.assertTrue(self.generator.item_allowed(record[1], record[2]), comment)

    def test_level_100_with_no_pp_ups_and_the_happiness_return_wants(self):
        for record, comment in self.records:
            level, _, _, unk, *moves = record[:8]
            pp_ups, happiness = record[8], record[9]
            self.assertEqual((level, unk, pp_ups, record[0x16:]), (100, 0, 0, b"\0\0"), comment)
            if 216 in moves:     # Return
                self.assertEqual(happiness, 255, comment)
            elif 218 in moves:   # Frustration
                self.assertEqual(happiness, 0, comment)
            else:
                self.assertEqual(happiness, 127, comment)

    def test_the_rule_set_alone_gets_them(self):
        source = RENTALS_SOURCE.read_text(encoding="ascii")
        self.assertIn('#include "rental_ou.inc.c"', source)
        self.assertIn("*gChosenRules == CHOSEN_OU ? NUM_OU_RENTALS : 0", source)


if __name__ == "__main__":
    unittest.main()
