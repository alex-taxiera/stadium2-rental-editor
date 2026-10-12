"""What happens to an edited rental afterwards, and the editor under other set-ups.

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import unittest

import gen_name_keys
import harness as h
from harness import DOWN, RIGHT, UP, EditState, Record, press, presses

# In the editor: happiness to 0, Attack DV to 15, then a name of Z, z, the PK sign and the
# female sign.
EDIT = (presses(DOWN, 4) + press(RIGHT) + press("A") + press("L") + press("A") + presses(UP, 4)
        + press(RIGHT) + press("A") + press("R") + press("A")
        + press(UP) + press("A", 20) + presses("B", 4) + presses(DOWN, 2) + presses(RIGHT, 7) + press("A")
        + press("R") + press("A") + press(DOWN) + press("A") + press("L") + press("A")
        + press("Start") + press("A", 20))
NAME = b"Zz\xBC\xBE"
# The same name as a saved team holds it: in the Game Boy's character codes, ended by 0x50.
GAME_BOY_CODE = {code: game_boy for code, game_boy, _ in gen_name_keys.KEYS.values()}
SAVED_NAME = bytes(GAME_BOY_CODE[code] for code in NAME) + b"\x50"
SAVED_SIZE = 0x24   # a saved Pokemon: this much of its record, then its names
# Out of the editor and Yes: the Pokemon is entered.
ENTER = press("B", 30) + press("A", 90)
# From there to the first turn of a battle against one of the computer's rentals.
TO_BATTLE = (press("Start", 60) + press("A", 240) + h.RENTAL_ONLY + h.ENTER_FIRST + ["wait 160"]
             + press("A", 300) + press("A", 300) + press("B", 60) + press("A", 120) + press("A", 1300))


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class EnteredPokemonTest(h.EmulatorTest):
    def edit(self) -> Record:
        self.start(*h.OPEN_EDITOR, *EDIT)
        record = self.s.record()
        self.assertEqual((record.happiness, record.dvs, record.nickname), (0, 0xFAA9, NAME))
        self.assertStatsFollow(record)
        return record

    def test_edits_reach_the_party_and_the_battle(self):
        edited = self.edit()
        self.do(*ENTER)
        self.assertEqual(self.s.party().data, edited.data)

        self.do(*TO_BATTLE)
        self.assertEqual(self.s.fragment(h.MOD_VRAM), (0, 0), "the mod is still loaded during the battle")
        self.assertEqual(self.s.fragment(h.PICKER_VRAM), (0, 0))
        fighting = Record(self.s.read(h.BATTLE_RECORD, h.RECORD_SIZE))
        self.assertEqual(fighting.editable, edited.editable)

    def test_a_registered_team_keeps_its_edits(self):
        edited = self.edit()
        # Yes, then Start and "OK to Register".
        self.do(*ENTER, *press("Start", 60), *press(DOWN, 15), *press("A", 500))

        self.s.reboot()
        signature = edited.data[:0x1C]   # species to PP: nothing else in memory looks like it
        self.assertEqual(self.s.find(signature), [], "the console's memory survived the reboot")

        # Free Battle again, and this time Registered POKeMON.
        self.do(*h.SCENES["picker"][:-len(h.RENTAL_ONLY)], *press("A", 300))
        # The team is in memory in both shapes: as it is saved, and unpacked into records.
        saved = records = 0
        for address in self.s.find(signature):
            data = self.s.read(address, h.RECORD_SIZE)
            if data[SAVED_SIZE:SAVED_SIZE + len(SAVED_NAME)] == SAVED_NAME:
                self.assertEqual(data[:SAVED_SIZE], edited.data[:SAVED_SIZE])
                saved += 1
            else:
                self.assertEqual(Record(data).editable, edited.editable)
                records += 1
        self.assertGreater(saved, 0, "the saved team was not read from the cartridge")
        self.assertGreater(records, 0, "the registered Pokemon was not loaded")


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class PokeCupTest(h.EmulatorTest):
    scene = "cup"

    def test_level_is_held_to_the_rules(self):
        self.start(*h.OPEN_EDITOR, *presses(DOWN, 4), *press("A"))
        self.assertEqual(self.s.edit_state().mode, EditState.ADJUST)
        for button, level in (("R", 55), (UP, 55), ("L", 50), (DOWN, 50), (UP, 51), (RIGHT, 55)):
            self.do(*press(button))
            record = self.s.record()
            self.assertEqual(record.level, level, button)
            self.assertStatsFollow(record)


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class TwoPlayerTest(h.EmulatorTest):
    scene = "two"

    def test_only_the_players_own_controller_drives_the_editor(self):
        self.start("player 2", *h.OPEN_EDITOR)
        state = self.s.edit_state()
        self.assertEqual(state.mode, EditState.FIELDS)
        self.assertEqual(self.s.panel(state).controller, 1)
        before = self.s.record()

        def snapshot():
            s = self.s.edit_state()
            return s.mode, s.col, s.row, s.on_name, s.name, s.key_col, s.key_row, s.key_page

        idle = snapshot()
        everything = press("A") + press("B") + press(DOWN) + press(RIGHT) + press("Start") + press("L") + press("R")
        self.do("player 1", *everything)
        self.assertEqual(snapshot(), idle)
        self.assertEqual(self.s.record().data, before.data)

        self.do("player 2", *press(RIGHT), *press("A"), *press("R"), *press("A"))
        self.assertEqual(self.s.record().dvs, 0xFAA9)

        # The same on the keyboard.
        self.do(*press(UP), *press("A", 20))
        typing = snapshot()
        self.assertEqual(typing[0], EditState.NAME)
        self.do("player 1", *everything)
        self.assertEqual(snapshot(), typing)
        self.do("player 2", *press("A"), *press("Start"), *press("A", 20), "player 1")
        self.assertEqual(self.s.record().nickname, b"ABRAA")


if __name__ == "__main__":
    unittest.main()
