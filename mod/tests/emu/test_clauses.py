"""The move clauses and the mod's own rule set, played in the emulator: 1P vs COM, under
"OU Rules" from Free Battle's list of the player's own rule sets.

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import struct
import unittest

import harness as h
import screens
from harness import DOWN, UP, EditState, Menu, Panel, Rules, press, presses
from test_editor import to_list_entry
from test_teams import OK_TO_BATTLE

DOUBLE_TEAM, MINIMIZE, GUILLOTINE, HORN_DRILL, FISSURE = 104, 107, 12, 32, 90
BATON_PASS, MEAN_LOOK, SPIDER_WEB = 226, 212, 169
SINGLE_BANS = {DOUBLE_TEAM, MINIMIZE, GUILLOTINE, HORN_DRILL, FISSURE}
DIGLETT, ARIADOS = 50, 168
SAND_ATTACK = 28

# The picker lists the rentals by name, four to a row. Diglett, the 37th, is the first
# of its row, and knows Earthquake, Slash, Fissure and Sand-Attack. Ariados is the last
# of the second row, and knows Sludge Bomb, Protect, Toxic and Spider Web.
TO_DIGLETT = presses(DOWN, 9, 12)
TO_ARIADOS = presses(DOWN, 1, 12) + presses(h.RIGHT, 3, 12)
# The ENTER menu's rows.
YES, NO, ITEM, EDIT = range(4)

# What the rule viewer says of a rule set with every clause.
CLAUSES_TITLE = b"Moves that cannot be known"
CLAUSES_TEXT = (b"No POK\xE9MON may know DOUBLE TEAM or MINIMIZE.\n"
                b"No POK\xE9MON may know FISSURE, GUILLOTINE or HORN DRILL.\n"
                b"No POK\xE9MON may know BATON PASS together with MEAN LOOK\nor SPIDER WEB.")


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class RuleSelectTest(h.EmulatorTest):
    """Free Battle's rule sets, where the mod's is offered and can be read."""

    scene = "rules"

    def test_the_rule_set_is_offered_after_the_players_own(self):
        self.start(*h.OWN_RULES)
        own = self.s.own_rules()
        self.assertEqual([rules.name for rules in own], [b"OU Rules"])
        rules = own[0]
        stock, cup = Rules(h.rom_bytes(h.ANYTHING_GOES, h.RULES_SIZE)), Rules(h.rom_bytes(h.POKE_CUP, h.RULES_SIZE))
        # Anything Goes, with the Poke Cup's species and the clauses, and named by itself.
        self.assertEqual(rules.species, cup.species)
        self.assertEqual([species for species in range(1, 252) if not rules.admits(species)],
                         [150, 151, 249, 250, 251])
        self.assertEqual(rules.flags, stock.flags | h.CLAUSES)
        self.assertEqual((rules.kind, rules.levels, rules.level_total, rules.background, rules.rentals),
                         (stock.kind, stock.levels, stock.level_total, stock.background, stock.rentals))
        self.assertLess(rules.name_text, 0)
        # The mod was in memory to put it there, and is not found there any more.
        self.assertEqual(self.s.fragment(h.MOD_VRAM), (0, 0))

    def test_the_viewer_says_what_the_clauses_keep_out(self):
        self.start(*h.OWN_RULES, *press("R", 150))
        heading, lines = self.s.viewer()
        self.assertEqual(heading, b"Check rule OU Rules")
        self.assertEqual(len(lines), 9)
        self.assertEqual(lines[0][0], b"Qualifying POK\xE9MON: 246 kinds")
        self.assertEqual(lines[-1], (CLAUSES_TITLE, CLAUSES_TEXT))
        # The line can be opened like the game's own, and the viewer left.
        self.do(*presses(DOWN, 8, 20), *press("A", 60))
        screens.check(self, "viewer_clauses", self.s.shot("viewer_clauses"), screens.VIEWER)
        self.do(*press("B", 60), *press("B", 150))
        self.assertEqual(self.s.fragment(h.VIEWER_VRAM), (0, 0))
        self.assertEqual(self.s.fragment(h.MOD_VRAM), (0, 0))
        self.assertEqual([rules.name for rules in self.s.own_rules()], [b"OU Rules"])

    def test_the_viewer_says_of_anything_goes_what_it_did(self):
        self.start(*press("R", 150))
        heading, lines = self.s.viewer()
        self.assertEqual(heading, b"Check rule Anything Goes")
        self.assertEqual([title for title, _ in lines],
                         [b"Open to all POK\xE9MON", b"Enter with the desired no. of POK\xE9MON",
                          b"One to four players may compete", b"No level restrictions", b"Same items can be held",
                          b"No two POK\xE9MON asleep or frozen", b"Rules on the final POK\xE9MON", b"Multiplayer"])

    def test_choosing_it_is_noted_and_choosing_another_is_not(self):
        self.start()
        self.assertEqual(self.s.read(h.CHOSEN_RULES, 1), b"\0")
        self.do(*h.OWN_RULES, *press("A", 120, 6), *press("A", 300, 6))
        self.assertEqual(self.s.read(h.CHOSEN_RULES, 1), b"\1")
        # Back from the entry screen to the rule sets, and Anything Goes this time.
        self.do(*press("B", 300), *press("B", 60))
        self.assertNotEqual(self.s.fragment(h.RULE_SELECT_VRAM), (0, 0))
        self.assertEqual(self.s.read(h.CHOSEN_RULES, 1), b"\0")
        self.do(*presses(UP, 5, 20), *press("A", 120, 6), *press("A", 300, 6))
        self.assertEqual(self.s.read(h.CHOSEN_RULES, 1), b"\0")
        self.assertEqual(self.s.rules().address, h.ANYTHING_GOES)


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class ClausesTest(h.EmulatorTest):
    """The rental picker under the mod's rule set."""

    scene = "ou"

    def list_for(self, slot: int) -> EditState:
        """With the editor open on its first move: opens the list of moves for a slot."""
        self.do(*presses(DOWN, slot), *press("A", 30))
        state = self.s.edit_state()
        self.assertEqual(state.mode, EditState.MOVE_LIST)
        return state

    def test_the_entry_screen_has_the_rule_set_and_the_session_anything_goes(self):
        self.start()
        rules = self.s.rules()
        session = self.s.u32(h.SESSION)
        self.assertEqual(rules.address, session + 0x3C)
        self.assertEqual(rules.data, self.s.read(session + 0x3C, h.RULES_SIZE))
        self.assertEqual((rules.name, rules.kind, rules.flags & h.CLAUSES), (b"OU Rules", 5, h.CLAUSES))
        # The session's mode and kind of rules are Anything Goes's.
        self.assertEqual(struct.unpack(">Hhhh", self.s.read(session, 8))[::3], (0x0220, 5))

    def test_a_rental_with_a_banned_move_is_refused_until_it_is_edited(self):
        self.start(*TO_DIGLETT, *h.OPEN_PANEL)
        panel = self.s.picker_panel()
        record = h.Record(self.s.read(panel.pokemon, h.RECORD_SIZE))
        self.assertEqual((record.species, record.moves[2]), (DIGLETT, FISSURE))
        # "Yes" is greyed out and the cursor starts on EDIT; Fissure is greyed out too.
        self.assertEqual((panel.state, panel.mode, panel.cursor), (Panel.MENU, Panel.ENTER, EDIT))
        shot = self.s.shot("clause_refused")
        screens.check(self, "clause_refused", shot, screens.SIDEBAR)
        screens.check(self, "clause_refused_moves", shot, screens.PANEL_MOVES)
        # The cursor cannot be put on "Yes", and ITEM, which would enter it, does nothing.
        self.do(*presses(UP, 4, 12))
        self.assertEqual(self.s.picker_panel().cursor, NO)
        self.do(*press(DOWN, 12), *press("A", 30))
        panel = self.s.picker_panel()
        self.assertEqual((panel.state, panel.cursor), (Panel.MENU, ITEM))
        self.assertEqual(self.s.party().species, 0)

        # The editor does not offer what the clauses keep out, and offers the rest.
        self.do(*press(DOWN, 12), *press("A", 30))
        state = self.list_for(2)
        legal = h.legal_moves(DIGLETT)
        self.assertEqual(set(legal) & SINGLE_BANS, {FISSURE, DOUBLE_TEAM})
        self.assertEqual(state.list, [0] + [move for move in legal if move not in SINGLE_BANS])
        # Fissure itself is not there to be kept, so the cursor is on the first entry,
        # which takes the move away. With that, the Pokemon can be entered.
        self.assertEqual(state.cursor, 0)
        self.do(*press("A", 30), *press("B", 30))
        panel = self.s.picker_panel()
        self.assertEqual((panel.state, panel.cursor), (Panel.MENU, YES))
        shot = self.s.shot("clause_fixed")
        screens.check(self, "clause_fixed", shot, screens.SIDEBAR)
        screens.check(self, "clause_fixed_moves", shot, screens.PANEL_MOVES)
        self.do(*press("A", 90))
        entered = self.s.party()
        self.assertEqual((entered.species, entered.moves), (DIGLETT, [89, 163, SAND_ATTACK, 0]))

    def test_baton_pass_and_a_trapping_move_keep_each_other_out(self):
        self.start(*TO_ARIADOS, *h.OPEN_PANEL)
        panel = self.s.picker_panel()
        record = h.Record(self.s.read(panel.pokemon, h.RECORD_SIZE))
        self.assertEqual((record.species, record.moves[3]), (ARIADOS, SPIDER_WEB))
        self.assertIn(BATON_PASS, h.legal_moves(ARIADOS))
        # Spider Web alone is no reason to refuse it.
        self.assertEqual(panel.cursor, YES)

        # Beside Spider Web, no other slot is offered Baton Pass.
        self.do(*presses(DOWN, 3), *press("A", 30))
        state = self.list_for(0)
        self.assertNotIn(BATON_PASS, state.list)
        self.assertIn(SPIDER_WEB, h.legal_moves(ARIADOS))
        # Spider Web's own slot is, in its place.
        self.do(*press("B", 20))
        state = self.list_for(3)
        self.assertIn(BATON_PASS, state.list)
        self.assertEqual(state.list[state.cursor], SPIDER_WEB)
        self.do(*to_list_entry(state.list.index(BATON_PASS), state.cursor), *press("A", 30))
        self.assertEqual(self.s.record().moves[3], BATON_PASS)
        # And beside Baton Pass, no other slot is offered Spider Web.
        self.do(*presses(UP, 3))
        state = self.list_for(0)
        self.assertNotIn(SPIDER_WEB, state.list)
        self.assertIn(BATON_PASS, state.list)   # a move already known is listed, as in any list

        # A Pokemon that knows both is refused like one with Fissure. (The editor gives no
        # way to make one, so the record is written to.)
        self.do(*press("B", 20), *press("B", 30), *press("B", 60))
        self.assertEqual(self.s.picker_panel().state, Panel.CLOSED)
        self.do(f"write {panel.pokemon + 2:08X} {bytes([BATON_PASS, 182, 92, SPIDER_WEB]).hex()}", *h.OPEN_PANEL)
        panel = self.s.picker_panel()
        self.assertEqual((panel.state, panel.cursor), (Panel.MENU, EDIT))
        screens.check(self, "clause_pair_moves", self.s.shot("clause_pair"), screens.PANEL_MOVES)

    def test_a_battle_is_one_of_anything_goes(self):
        # One Pokemon is a team, as only Anything Goes has it, and it fights.
        self.start(*h.TEAM_MENU)
        self.assertEqual(self.s.party_state(), h.PARTY_MENU)
        entered = self.s.party()
        self.do(*OK_TO_BATTLE)
        self.assertEqual(self.s.fragment(h.MOD_VRAM), (0, 0))
        self.assertEqual(self.s.fragment(h.PICKER_VRAM), (0, 0))
        fighting = h.Record(self.s.read(h.BATTLE_RECORD, h.RECORD_SIZE))
        self.assertEqual(fighting.editable, entered.editable)


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class AnythingGoesTest(h.EmulatorTest):
    """The clauses are the rule set's: Anything Goes has none."""

    def test_anything_goes_refuses_nothing(self):
        self.start(*TO_DIGLETT, *h.OPEN_PANEL)
        self.assertEqual(self.s.read(h.CHOSEN_RULES, 1), b"\0")
        rules = self.s.rules()
        self.assertEqual(rules.address, h.ANYTHING_GOES)
        self.assertEqual(rules.data, h.rom_bytes(h.ANYTHING_GOES, h.RULES_SIZE))
        panel = self.s.picker_panel()
        self.assertEqual((panel.state, panel.cursor), (Panel.MENU, YES))
        shot = self.s.shot("clause_none")
        screens.check(self, "clause_none", shot, screens.SIDEBAR)
        screens.check(self, "clause_none_moves", shot, screens.PANEL_MOVES)
        # The editor offers Fissure, which Diglett knows, and Double Team.
        self.do(*presses(DOWN, 3), *press("A", 30), *presses(DOWN, 2), *press("A", 30))
        state = self.s.edit_state()
        self.assertEqual(state.list, [0] + h.legal_moves(DIGLETT))
        self.assertEqual(state.list[state.cursor], FISSURE)
        # And it is entered as it is.
        self.do(*press("B", 20), *press("B", 30), *press("A", 90))
        entered = self.s.party()
        self.assertEqual((entered.species, entered.moves[2]), (DIGLETT, FISSURE))


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class RegisteredTeamTest(h.EmulatorTest):
    """A registered team is entered whole. The mod's rule set shares Anything Goes's."""

    def test_a_registered_team_the_rules_refuse_cannot_be_chosen(self):
        # Under Anything Goes: Diglett, with Fissure, registered as a team.
        self.start(*TO_DIGLETT, *h.OPEN_PANEL, *press("A", 90), *press("Start", 60), *press(DOWN, 15),
                   *press("A", 500))
        self.s.reboot()

        # Under the mod's rule set its OK is greyed out, and does nothing.
        self.do(*h.SCENES["ou entry"], *press("A", 300), *press("A", 60))
        menu = self.s.team_menu()
        self.assertEqual((menu.status, menu.cursor, menu.count), (Menu.OPEN, 0, 3))
        screens.check(self, "set_refused", self.s.shot("set_refused"), screens.SET_MENU)
        self.do(*press("A", 60))
        menu = self.s.team_menu()
        self.assertEqual((menu.status, menu.cursor), (Menu.OPEN, 0))
        self.assertEqual(self.s.side(), 0)
        # "Check" shows why: the move is greyed out.
        self.do(*presses(DOWN, 2, 12), *press("A", 90), *press("A", 60))
        shown = self.s.picker_panel()
        self.assertEqual(h.Record(self.s.read(shown.pokemon, h.RECORD_SIZE)).moves[2], FISSURE)
        screens.check(self, "set_refused_moves", self.s.shot("set_refused_check"), screens.PANEL_MOVES)

        # Under Anything Goes the same team is chosen as ever.
        self.s.reboot()
        self.do(*h.SCENES["picker"][:-len(h.RENTAL_ONLY)], *press("A", 300), *press("A", 60))
        screens.check(self, "set_accepted", self.s.shot("set_accepted"), screens.SET_MENU)
        self.assertEqual(self.s.side(), 0)
        self.do(*press("A", 240))
        self.assertEqual(self.s.side(), 1)   # and it is the COM's turn to choose


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class RuleEditorTest(h.EmulatorTest):
    """RULE EDIT, under OPTIONS, where a rule set of the player's own gets the clauses."""

    PAGE, OK_ROW = 4, 9          # what RULE EDIT shows for one rule set, and that page's last row
    EVASION, OHKO, TRAP_PASS = 6, 7, 8   # the clauses' rows, after the game's six
    CUSTOM = 0xE                 # the kind of a player's own rule set

    def test_a_rule_set_of_the_players_own_keeps_its_clauses(self):
        self.s.emulator.reboot()
        self.do("turbo on", *h.SELECT, *h.RULE_EDIT)
        base, size = self.s.fragment(h.MOD_VRAM)
        self.assertNotEqual(base, 0)
        self.assertEqual(size, self.s.mod_size)
        self.assertEqual(self.s.edited_rules(), [])

        # A new rule set has no clauses, and its page has a row for each, saying "Use".
        self.do(*h.MAKE_RULES)
        mode, cursor, rules = self.s.rule_page()
        self.assertEqual((mode, cursor, rules.kind, rules.flags & h.CLAUSES), (self.PAGE, 0, self.CUSTOM, 0))
        # The page's window is higher than the game has it, for the rows to fit.
        editor, _ = self.s.fragment(h.RULE_EDIT_VRAM)
        window = struct.unpack(">4h", self.s.read(editor + h.RULE_EDIT_WINDOW - h.RULE_EDIT_VRAM, 8))
        self.assertEqual(window, (74, 93, 498, 356))
        screens.check(self, "rule_page", self.s.shot("rule_page"), screens.RULE_PAGE)

        # Down past the game's rows to the first of the mod's: A answers it the other way.
        self.do(*presses(DOWN, 6, 20))
        self.assertEqual(self.s.rule_page()[1], self.EVASION)
        self.do(*press("A", 20))
        self.assertEqual(self.s.rule_page()[2].flags & h.CLAUSES, 1)
        self.do(*press("A", 20))
        self.assertEqual(self.s.rule_page()[2].flags & h.CLAUSES, 0)
        self.do(*press("A", 20), *presses(DOWN, 2, 20), *press("A", 20))
        mode, cursor, rules = self.s.rule_page()
        self.assertEqual((mode, cursor, rules.flags & h.CLAUSES), (self.PAGE, self.TRAP_PASS, 5))
        screens.check(self, "rule_page_clauses", self.s.shot("rule_page_clauses"), screens.RULE_PAGE)
        # The game's flags are as it made them: the clauses are other bits.
        stock_flags = rules.flags & ~h.CLAUSES
        self.assertEqual(stock_flags, 0x0C000000)

        # OK is the row after, and the cursor goes round from it to the first.
        self.do(*press(DOWN, 20))
        self.assertEqual(self.s.rule_page()[1], self.OK_ROW)
        self.do(*press(DOWN, 20))
        self.assertEqual(self.s.rule_page()[1], 0)
        self.do(*press(UP, 20))
        self.assertEqual(self.s.rule_page()[1], self.OK_ROW)
        screens.check(self, "rule_page_ok", self.s.shot("rule_page_ok"), screens.RULE_PAGE)
        self.do(*press("A", 200))
        kept = self.s.edited_rules()
        self.assertEqual([(rules.name, rules.kind, rules.flags) for rules in kept],
                         [(b"Edit rule 1", self.CUSTOM, stock_flags | 5)])

        # Saved, and read again after the power has been off: Free Battle lists it before
        # the mod's own rule set, with its clauses, and the viewer says which.
        self.do(*h.SAVE_RULES)
        self.assertEqual(self.s.fragment(h.RULE_EDIT_VRAM), (0, 0))
        self.s.reboot()
        self.do(*h.SCENES["rules"], *h.OWN_RULES)
        own = self.s.own_rules()
        self.assertEqual([rules.name for rules in own], [b"Edit rule 1", b"OU Rules"])
        self.assertEqual((own[0].kind, own[0].flags, own[0].species), (self.CUSTOM, stock_flags | 5, kept[0].species))
        self.do(*press("R", 150))
        heading, lines = self.s.viewer()
        self.assertEqual(heading, b"Check rule Edit rule 1")
        evasion, _, trap_pass = CLAUSES_TEXT.split(b"\n", 2)
        self.assertEqual(lines[-1], (CLAUSES_TITLE, evasion + b"\n" + trap_pass))


if __name__ == "__main__":
    unittest.main()
