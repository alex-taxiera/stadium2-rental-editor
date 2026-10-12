"""What happens to an edited rental afterwards, and the editor under other set-ups.

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import unittest

import gen_name_keys
import harness as h
import screens
from harness import DOWN, RIGHT, UP, EditState, Menu, Panel, Record, press, presses

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
# From the team's menu on OK to the first turn of a battle against one of the computer's
# rentals, and the same from before the menu is up.
OK_TO_BATTLE = (press("A", 240) + h.RENTAL_ONLY + h.ENTER_FIRST + ["wait 160"]
                + press("A", 300) + press("A", 300) + press("B", 60) + press("A", 120) + press("A", 1300))
TO_BATTLE = press("Start", 60) + OK_TO_BATTLE
# In the editor as it opens: Attack DV to 15, or Attack Stat Exp to nothing.
ATTACK_DV = press(RIGHT) + press("A") + press("R") + press("A")
ATTACK_STAT_EXP = presses(RIGHT, 2) + press("A") + press("L") + press("A")


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
class TeamMemberTest(h.EmulatorTest):
    """The editor on a Pokemon that is already on the team, which stays there meanwhile."""

    def assertEditing(self, index: int, direct: int) -> None:
        state = self.s.edit_state()
        panel = self.s.panel(state)
        self.assertEqual((state.mode, state.direct), (EditState.FIELDS, direct))
        self.assertEqual((panel.state, panel.mode, panel.pokemon),
                         (Panel.MENU, Panel.EXCHANGE, self.s.party_cell(index)))

    def test_edit_joins_yes_and_no_for_one_of_the_team(self):
        self.start(*h.TEAM_MENU, *h.RESELECT_SOME)
        self.assertEqual(self.s.party_state(), h.PARTY_BOX)
        entered = self.s.party()

        self.do(*h.OPEN_MEMBER)
        screens.check(self, "exchange_menu", self.s.shot("exchange_menu"), screens.SIDEBAR)
        self.do(*h.EXCHANGE_EDIT)
        self.assertEditing(0, direct=0)
        screens.check(self, "team_editor", self.s.shot("team_editor"))

        self.do(*ATTACK_DV)
        edited = self.s.party()
        self.assertEqual(edited.dvs, 0xFAA9)
        self.assertNotEqual(edited.dvs, entered.dvs)
        self.assertStatsFollow(edited)

        # B is back on the menu, and on No: Yes would give the Pokemon up for another.
        self.do(*press("B", 30))
        panel = self.s.panel()
        self.assertEqual((self.s.edit_state().mode, panel.state, panel.cursor), (EditState.OFF, Panel.MENU, Panel.NO))
        # No leaves the cursor in the team's box, and B there brings the team's menu back.
        self.do(*press("A", 40))
        self.assertEqual((self.s.panel().state, self.s.party_state()), (Panel.CLOSED, h.PARTY_BOX))
        self.do(*press("B", 40))
        self.assertEqual((self.s.party_state(), self.s.team_menu().status), (h.PARTY_MENU, Menu.OPEN))
        self.assertEqual(self.s.party().data, edited.data)

    def test_edit_pokemon_opens_the_editor_on_one_of_the_team(self):
        self.start(*h.TEAM_MENU, *h.EDIT_POKEMON)
        self.assertEqual((self.s.party_state(), self.s.edit_state().pending), (h.PARTY_BOX, 1))
        # The game takes it for Reselect some, but the question is the editor's.
        screens.check(self, "edit_which", self.s.shot("edit_which"), screens.TEAM_QUESTION)
        icon = self.s.read(self.s.party_cell() + h.CELL_ICON, h.ICON_SIZE)

        self.do(*h.OPEN_MEMBER)
        self.assertEditing(0, direct=1)
        self.do(*EDIT)
        edited = self.s.party()
        self.assertEqual((edited.happiness, edited.dvs, edited.nickname), (0, 0xFAA9, NAME))
        self.assertStatsFollow(edited)
        self.assertNotEqual(self.s.read(self.s.party_cell() + h.CELL_ICON, h.ICON_SIZE), icon,
                            "a name tints the Pokemon, in the team's box too")

        # B closes it with no menu in between, the cursor back in the team's box for the
        # next one; and the next one is the same again.
        self.do(*press("B", 40))
        self.assertEqual((self.s.edit_state().mode, self.s.panel().state, self.s.party_state()),
                         (EditState.OFF, Panel.CLOSED, h.PARTY_BOX))
        screens.check(self, "team_edited", self.s.shot("team_edited"))
        self.do(*h.OPEN_MEMBER)
        self.assertEditing(0, direct=1)

        # B twice is the team's menu, on OK, and nobody is waiting for the editor.
        self.do(*presses("B", 2, 40))
        self.assertEqual((self.s.party_state(), self.s.team_menu().status, self.s.team_menu().cursor),
                         (h.PARTY_MENU, Menu.OPEN, 0))
        self.assertEqual(self.s.edit_state().pending, 0)
        # Reselect some is what it was: the menu, not the editor.
        self.do(*h.RESELECT_SOME, *h.OPEN_MEMBER)
        panel = self.s.panel()
        self.assertEqual((self.s.edit_state().mode, panel.state, panel.mode, panel.cursor),
                         (EditState.OFF, Panel.MENU, Panel.EXCHANGE, Panel.YES))

    def test_edits_made_before_entering_are_kept_and_added_to(self):
        self.start(*h.OPEN_EDITOR, *EDIT, *ENTER)
        entered = self.s.party()
        self.assertEqual((entered.happiness, entered.dvs, entered.nickname), (0, 0xFAA9, NAME))
        self.assertNotEqual(entered.stat_exp[1], 0)

        self.do(*press("Start", 60), *h.EDIT_POKEMON, *h.OPEN_MEMBER, *ATTACK_STAT_EXP, *presses("B", 2, 40))
        edited = self.s.party()
        self.assertEqual(edited.stat_exp, [entered.stat_exp[0], 0] + entered.stat_exp[2:])
        self.assertEqual((edited.happiness, edited.dvs, edited.nickname, edited.moves),
                         (0, 0xFAA9, NAME, entered.moves))
        self.assertStatsFollow(edited)

        self.do(*OK_TO_BATTLE)
        fighting = Record(self.s.read(h.BATTLE_RECORD, h.RECORD_SIZE))
        self.assertEqual(fighting.editable, edited.editable)

    def test_the_others_of_the_team_are_left_alone(self):
        # Two rentals entered, and the second edited.
        self.start(*press("A", 60), *press("A", 90), *press(RIGHT, 20), *press("A", 60), *press("A", 90),
                   *press("Start", 60))
        first, second = self.s.party(0), self.s.party(1)
        self.assertNotEqual(second.species, 0)
        self.do(*h.EDIT_POKEMON, *press(RIGHT, 20), *h.OPEN_MEMBER)
        self.assertEditing(1, direct=1)
        self.do(*ATTACK_DV)
        self.assertEqual(self.s.party(0).data, first.data)
        self.assertEqual(self.s.party(1).dvs, (second.dvs & 0x0FFF) | 0xF000)
        self.assertStatsFollow(self.s.party(1))


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

    def test_a_level_cannot_take_the_team_past_the_rules(self):
        # Six rentals, which under these rules is what it takes for the team's menu.
        # Their three lowest levels may come to 155, and all six are at 50.
        another = press(RIGHT, 20) + press("A", 60) + press("A", 90)
        self.start(*press("A", 60), *press("A", 90), *(another * 5), "wait 60")
        self.assertEqual((self.s.party_state(), self.s.team_menu().status), (h.PARTY_MENU, Menu.OPEN))
        self.assertEqual([self.s.party(i).level for i in range(6)], [50] * 6)

        # From the team the range is the same as from the list.
        to_level = presses(DOWN, 4) + press("A")
        self.do(*h.EDIT_POKEMON, *h.OPEN_MEMBER, *to_level)
        for button, level in (("R", 55), (UP, 55), ("L", 50), (DOWN, 50), (UP, 51), (RIGHT, 55)):
            self.do(*press(button))
            self.assertEqual(self.s.party().level, level, button)
            self.assertStatsFollow(self.s.party())

        # Four at 55 leave 50, 50 and 55 the lowest: just within. The box is three wide,
        # so the way round it is right, right, down, left.
        raise_it = h.OPEN_MEMBER + to_level + press("R") + press("A") + press("B", 40)
        self.do(*press("A"), *press("B", 40), *press(RIGHT, 20), *raise_it, *press(RIGHT, 20), *raise_it,
                *press(DOWN, 20), *raise_it)
        self.assertEqual([self.s.party(i).level for i in range(6)], [55, 55, 55, 50, 50, 55])
        # A fifth would not be, at any level above its own.
        self.do(*press(h.LEFT, 20), *h.OPEN_MEMBER, *to_level)
        before = self.s.party(4)
        for button in ("R", RIGHT, UP):
            self.do(*press(button))
            self.assertEqual(self.s.party(4).data, before.data, button)
        # So the team's menu comes back, and the team is whole.
        self.do(*press("A"), *presses("B", 2, 40))
        self.assertEqual((self.s.party_state(), self.s.team_menu().status), (h.PARTY_MENU, Menu.OPEN))
        self.assertEqual([self.s.party(i).species != 0 for i in range(6)], [True] * 6)

        # With one of the four back at 50 there is room: the lowest are then all 50.
        self.do(*h.EDIT_POKEMON, *h.OPEN_MEMBER, *to_level, *press("L"), *press("A"), *press("B", 40),
                *press(RIGHT, 20), *press(DOWN, 20), *raise_it)
        self.assertEqual([self.s.party(i).level for i in range(6)], [50, 55, 55, 50, 55, 55])


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

    def test_only_the_players_own_controller_edits_their_team(self):
        self.start("player 2", *h.OPEN_TEAM_EDITOR)
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.direct, self.s.panel(state).controller), (EditState.FIELDS, 1, 1))
        before = self.s.party()

        everything = press("A") + press("B") + press(DOWN) + press(RIGHT) + press("Start") + press("L") + press("R")
        self.do("player 1", *everything)
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.col, state.row), (EditState.FIELDS, EditState.COL_MOVES, 0))
        self.assertEqual((self.s.party().data, self.s.party_state()), (before.data, h.PARTY_PANEL))

        self.do("player 2", *ATTACK_DV, *presses("B", 2, 40), "player 1")
        self.assertEqual((self.s.party().dvs, self.s.party_state()), (0xFAA9, h.PARTY_MENU))


if __name__ == "__main__":
    unittest.main()
