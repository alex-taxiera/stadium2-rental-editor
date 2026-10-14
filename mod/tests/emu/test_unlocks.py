"""What a Free Battle offers on a new save file, played in the emulator: every stage, and
every Pokemon for rent.

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import struct
import unittest

import harness as h
from harness import DOWN, Menu, Panel, Record, press, presses

NUM_STAGES = 30
MEWTWO, MEW, LUGIA, HO_OH, CELEBI = 150, 151, 249, 250, 251
EVERY = list(range(1, 252))
# The game's tables of rental Pokemon: Anything Goes's and the Prime Cup's, the one the
# Prime Cup has in Round 2, and the Poke Cup's.
LEVEL_100, ROUND_2, LEVEL_50 = 1, 2, 3
# The three the game has no rental of, as mod/data/rental_extra.inc.c has them: no DVs,
# no Stat Exp, and the moves of the Rival's in Round 2.
OWN = {MEWTWO: [94, 66, 85, 105], LUGIA: [177, 89, 94, 219], HO_OH: [221, 87, 89, 202]}
THUNDERBOLT = 85
RENTAL = 0x04   # in a record's flags


def species(records: list) -> list:
    return [record[1] for record in records]


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class StagesTest(h.EmulatorTest):
    """The tests' save file is empty, and has met a battle nowhere."""

    scene = "rules"

    def test_every_stage_is_on_the_list(self):
        self.start()
        self.assertEqual(self.s.stages(), list(range(NUM_STAGES)))


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class RentalsTest(h.EmulatorTest):
    """Under Anything Goes."""

    def test_the_list_has_every_pokemon(self):
        self.start()
        listed = self.s.rentals()
        self.assertEqual(species(listed), EVERY)
        # The game's 246 as a Free Battle has always had them, and its own Mew and Celebi.
        stock = {record[1]: record for record in h.rental_table(ROUND_2)}
        stock.update({record[1]: record for record in h.rental_table(LEVEL_100)})
        self.assertEqual([record for record in listed if record[1] not in OWN],
                         [stock[one] for one in EVERY if one not in OWN])
        # And the mod's three, as it has them.
        for record in listed:
            if record[1] in OWN:
                level, _, item, _, *moves, pp_ups, happiness = struct.unpack_from(">10B", record)
                self.assertEqual((level, item, moves, pp_ups, happiness), (100, 0, OWN[record[1]], 0, 127))
                self.assertEqual(record[10:22], bytes(12))

    def test_each_of_the_five_opens_as_itself(self):
        for one in (MEWTWO, MEW, LUGIA, HO_OH, CELEBI):
            with self.subTest(species=one):
                self.start(*h.to_rental(one, EVERY), *h.OPEN_PANEL)
                panel = self.s.picker_panel()
                self.assertEqual((panel.state, panel.mode), (Panel.MENU, Panel.ENTER))
                record = Record(self.s.read(panel.pokemon, h.RECORD_SIZE))
                self.assertEqual((record.species, record.level), (one, 100))
                self.assertTrue(record.flags & RENTAL)
                self.assertEqual((record.dvs, record.stat_exp), (0, [0] * 5))
                if one in OWN:
                    self.assertEqual(record.moves, OWN[one])
                self.assertStatsFollow(record)

    def test_mewtwo_is_edited_and_entered(self):
        self.start(*h.to_rental(MEWTWO, EVERY), *h.OPEN_EDITOR)
        record = self.s.record()
        self.assertEqual((record.species, record.nickname, record.moves), (MEWTWO, b"MEWTWO", OWN[MEWTWO]))
        # Its third move opens the list of Mewtwo's own.
        self.do(*presses(DOWN, 2), *press("A", 30))
        state = self.s.edit_state()
        self.assertEqual(state.list, [0] + h.legal_moves(MEWTWO))
        self.assertEqual(state.list[state.cursor], THUNDERBOLT)
        # Out of the list and the editor, and Yes.
        self.do(*press("B", 20), *press("B", 30), *press("A", 90))
        entered = self.s.party()
        self.assertEqual((entered.species, entered.level, entered.moves), (MEWTWO, 100, OWN[MEWTWO]))
        self.assertStatsFollow(entered)


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class OuRentalsTest(h.EmulatorTest):
    """The mod's own rule set keeps the five out, and lists nobody who may not enter."""

    scene = "ou"

    def test_the_list_is_the_games_own(self):
        self.start()
        self.assertEqual(self.s.rentals(), h.rental_table(LEVEL_100))


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class RegisteredTeamTest(h.EmulatorTest):
    """A registered team is entered whole, and the mod's rule set shares Anything Goes's
    teams: one with a Pokemon on it that the rule set keeps out cannot be chosen."""

    def test_a_team_with_mewtwo_on_it_is_refused_under_ou_rules(self):
        # Under Anything Goes: Mewtwo, Yes, Start and "OK to Register".
        self.start(*h.to_rental(MEWTWO, EVERY), *h.OPEN_PANEL, *press("A", 90), *press("Start", 60),
                   *press(DOWN, 15), *press("A", 500))
        self.s.reboot()

        # Under the mod's rule set, Registered POKeMON and the team: A on its OK does nothing.
        self.do(*h.SCENES["ou entry"], *press("A", 300), *press("A", 60))
        menu = self.s.team_menu()
        self.assertEqual((menu.status, menu.cursor, menu.count), (Menu.OPEN, 0, 3))
        self.do(*press("A", 60))
        menu = self.s.team_menu()
        self.assertEqual((menu.status, menu.cursor), (Menu.OPEN, 0))
        self.assertEqual(self.s.side(), 0)

        # Under Anything Goes the same team is chosen, and it is the COM's turn.
        self.s.reboot()
        self.do(*h.SCENES["picker"][:-len(h.RENTAL_ONLY)], *press("A", 300), *press("A", 60))
        self.assertEqual(self.s.side(), 0)
        self.do(*press("A", 240))
        self.assertEqual(self.s.side(), 1)


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class CupRentalsTest(h.EmulatorTest):
    """So does the Poke Cup, whose table is another."""

    scene = "cup"

    def test_the_list_is_the_games_own(self):
        self.start()
        self.assertEqual(self.s.rentals(), h.rental_table(LEVEL_50))


if __name__ == "__main__":
    unittest.main()
