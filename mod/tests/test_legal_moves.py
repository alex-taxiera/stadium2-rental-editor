"""Move-legality table checks. Run: python3 -m unittest discover mod/tests

Needs the pinned source data in mod/data/cache (tools/mod/gen_legal_moves.py --fetch).
"""

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import gen_legal_moves as gen  # noqa: E402

RENTALS = gen.DEFAULT_CACHE / "rentals"
HAVE_DATA = all(gen.cache_path(gen.DEFAULT_CACHE, key).exists() for key in gen.SOURCES)

# Names in the old rental dumps that Showdown has since renamed or spells differently.
RENAMED = {"hijumpkick": "highjumpkick", "faintattack": "feintattack", "vicegrip": "visegrip"}
SPECIES_ALIASES = {"Nidoran♀": "nidoranf", "Nidoran♂": "nidoranm"}


@unittest.skipUnless(HAVE_DATA, "source data not cached; run gen_legal_moves.py --fetch")
class LegalMovesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = gen.Data(gen.DEFAULT_CACHE)
        cls.pokedex, cls.learnsets, cls.moves = cls.data.pokedex, cls.data.learnsets, cls.data.moves
        cls.table = cls.data.table()
        cls.with_events = cls.data.table(include_events=True)

    def legal(self, species, move, table=None):
        table = self.table if table is None else table
        return self.moves[move] in table[self.pokedex[species]["num"]]

    def test_sources_parse_cleanly(self):
        self.assertEqual(self.data.validate(), [])

    def test_covers_all_species_and_moves(self):
        self.assertEqual(sorted(self.table), list(range(1, 252)))
        self.assertEqual(sorted(set(self.moves.values())), list(range(1, 252)))
        self.assertEqual(self.moves["pound"], 1)
        self.assertEqual(self.moves["beatup"], 251)
        self.assertEqual(self.pokedex["celebi"]["num"], 251)
        for num, legal in self.table.items():
            self.assertTrue(legal, f"species {num} has no legal moves")

    def test_level_up_move(self):
        self.assertTrue(self.legal("bulbasaur", "razorleaf"))

    def test_tm_move(self):
        self.assertTrue(self.legal("bulbasaur", "gigadrain"))

    def test_egg_move(self):
        self.assertTrue(self.legal("bulbasaur", "lightscreen"))

    def test_gen1_tradeback_move(self):
        self.assertEqual(self.learnsets["bulbasaur"]["bodyslam"], {(1, "M")})
        self.assertTrue(self.legal("bulbasaur", "bodyslam"))

    def test_crystal_tutor_move(self):
        self.assertIn((2, "T"), self.learnsets["charmander"]["flamethrower"])
        self.assertTrue(self.legal("charmander", "flamethrower"))

    def test_earlier_stage_moves_are_inherited(self):
        self.assertNotIn("lightscreen", self.learnsets["venusaur"])
        self.assertTrue(self.legal("venusaur", "lightscreen"))
        self.assertTrue(self.legal("raichu", "charm"))  # Pichu level-up move

    def test_unlearnable_move_is_rejected(self):
        self.assertFalse(self.legal("bulbasaur", "flamethrower"))
        self.assertFalse(self.legal("magikarp", "surf"))

    def test_event_only_moves_are_rejected_by_default(self):
        self.assertEqual(self.learnsets["bulbasaur"]["ancientpower"], {(2, "S")})
        self.assertFalse(self.legal("bulbasaur", "ancientpower"))
        self.assertFalse(self.legal("dratini", "extremespeed"))
        self.assertFalse(self.legal("dragonite", "extremespeed"))
        self.assertTrue(self.legal("bulbasaur", "ancientpower", self.with_events))
        self.assertTrue(self.legal("dragonite", "extremespeed", self.with_events))

    def test_game_level_up_tables_fill_showdown_gaps(self):
        self.assertNotIn("conversion2", self.learnsets["porygon"])
        self.assertTrue(self.legal("porygon", "conversion2"))
        self.assertTrue(self.legal("porygon2", "tackle"))

    def test_sources_disagree_only_where_expected(self):
        report = self.data.report()
        self.assertEqual([line for line in report if line.startswith("level-up")], [
            "level-up in game data, missing from Showdown: porygon conversion2",
            "level-up in game data, missing from Showdown: porygon2 tackle",
        ])
        self.assertEqual([line for line in report if "missing from game data" in line], [])

    def test_unobtainable_gold_egg_moves_stay_illegal(self):
        self.assertIn("charm", self.data.egg["gold_egg"]["bulbasaur"])
        self.assertFalse(self.legal("bulbasaur", "charm"))
        self.assertFalse(self.legal("smoochum", "lovelykiss"))
        self.assertTrue(self.legal("jynx", "lovelykiss"))  # Jynx's own level-up move

    def test_smeargle_can_sketch_almost_anything(self):
        smeargle = self.table[self.pokedex["smeargle"]["num"]]
        self.assertEqual(len(smeargle), 248)
        for move in ("spore", "sketch", "transform", "aeroblast", "sacredfire"):
            self.assertTrue(self.legal("smeargle", move), move)
        for move in ("struggle", "explosion", "selfdestruct"):
            self.assertFalse(self.legal("smeargle", move), move)

    def test_single_move_species(self):
        self.assertEqual(self.table[self.pokedex["ditto"]["num"]], {self.moves["transform"]})
        self.assertEqual(self.table[self.pokedex["unown"]["num"]], {self.moves["hiddenpower"]})

    def test_packed_row_round_trips(self):
        legal = self.table[self.pokedex["mew"]["num"]]
        row = gen.pack_row(legal)
        self.assertEqual(len(row), 32)
        unpacked = {m for m in range(256) if row[m >> 3] >> (m & 7) & 1}
        self.assertEqual(unpacked, legal)

    def test_checked_in_table_is_current(self):
        self.assertTrue(gen.DEFAULT_OUT.exists(), "run tools/mod/gen_legal_moves.py")
        self.assertEqual(gen.DEFAULT_OUT.read_text(encoding="ascii"),
                         gen.render(self.table, self.pokedex, gen.alphabetical_moves(self.moves),
                                    include_events=False))

    def test_alphabetical_order_lists_every_move_once(self):
        order = gen.alphabetical_moves(self.moves)
        self.assertEqual(sorted(order), list(range(1, 252)))
        by_number = {number: name for name, number in self.moves.items() if not name.startswith("hiddenpower")}
        self.assertEqual([by_number[n] for n in order[:4]], ["absorb", "acid", "acidarmor", "aeroblast"])
        self.assertEqual(by_number[order[-1]], "zapcannon")
        # Sorted the way the game spells them: FAINT ATTACK, not Feint Attack.
        self.assertLess(order.index(self.moves["feintattack"]), order.index(self.moves["falseswipe"]))
        self.assertLess(order.index(self.moves["visegrip"]), order.index(self.moves["vinewhip"]))

    @unittest.skipUnless(RENTALS.is_dir(), "stock rental tables not cached")
    def test_stock_rentals(self):
        """The game's own rental movesets must pass, apart from event moves it hands out itself."""
        rejected = []
        total = 0
        for path in sorted(RENTALS.glob("*.json")):
            for mon in json.loads(path.read_text(encoding="utf-8")):
                species = SPECIES_ALIASES.get(mon["species"]) or gen.to_id(mon["species"])
                self.assertTrue(species in self.pokedex, f"unknown species {mon['species']!r}")
                for key in ("move1", "move2", "move3", "move4"):
                    if key not in mon:
                        continue
                    move = gen.to_id(mon[key])
                    move = RENAMED.get(move, move)
                    self.assertTrue(move in self.moves, f"unknown move {mon[key]!r}")
                    total += 1
                    if not self.legal(species, move):
                        self.assertTrue(self.legal(species, move, self.with_events),
                                        f"{mon['species']} {mon[key]} is in no learnset at all")
                        rejected.append((path.stem, mon["species"], mon[key]))
        self.assertEqual(total, 3248)
        self.assertEqual(rejected, [("primecup2", "Psyduck", "Amnesia")])


if __name__ == "__main__":
    unittest.main()
