"""The editor, played in the emulator: 1P vs COM, Anything Goes, the first rental (Abra).

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import unittest

import harness as h
import screens
from harness import DOWN, LEFT, RIGHT, UP, EditState, Panel, press, presses

LIST_PAGE = 7      # EDIT_LIST_ROWS
KEY_ROW_WIDE = 4   # the keyboard's bottom row: lower/UPPER, DEL, END
END_COLUMN = 7     # where the cursor rests on END


def to_list_entry(index: int, cursor: int) -> list:
    """Commands that move the move list's cursor from `cursor` to `index`."""
    return (presses(LEFT, -(-cursor // LIST_PAGE)) + presses(RIGHT, index // LIST_PAGE)
            + presses(DOWN, index % LIST_PAGE))


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class EditorTest(h.EmulatorTest):
    def test_mod_is_loaded_in_the_picker(self):
        self.start()
        base, size = self.s.fragment(h.MOD_VRAM)
        self.assertNotEqual(base, 0)
        self.assertEqual(size, self.s.mod_size)

    def test_first_rental_is_as_the_tests_expect(self):
        self.start(*h.OPEN_EDITOR)
        record = self.s.record()
        self.assertEqual(record.species, h.ABRA)
        self.assertEqual(record.moves[:2], [h.PSYCHIC, h.ICE_PUNCH])
        self.assertEqual((record.level, record.dvs, record.stat_exp), (100, 0x9AA9, [45000] * 5))
        self.assertEqual(record.nickname, b"ABRA")
        self.assertStatsFollow(record)

    def test_edit_entry_is_drawn_under_the_stock_ones(self):
        self.start(*h.OPEN_PANEL, *presses(DOWN, 3))
        screens.check(self, "edit_entry", self.s.shot("edit_entry"), screens.SIDEBAR)

    def test_editor_opens_and_closes(self):
        self.start(*h.OPEN_EDITOR)
        state = self.s.edit_state()
        panel = self.s.panel(state)
        self.assertEqual((state.mode, state.col, state.row, state.on_name), (EditState.FIELDS, 0, 0, 0))
        self.assertEqual((panel.state, panel.mode, panel.cursor), (Panel.MENU, 0, 3))
        shot = self.s.shot("fields")
        screens.check(self, "fields", shot)
        screens.check(self, "hints_fields", shot, screens.SIDEBAR)

        self.do(*press("B", 20))
        state = self.s.edit_state()
        panel = self.s.panel(state)
        self.assertEqual(state.mode, EditState.OFF)
        self.assertEqual((panel.state, panel.cursor), (Panel.MENU, 0))   # back on Yes

        # The stock menu still works: No closes the panel.
        self.do(*press(DOWN), *press("A", 60))
        self.assertNotEqual(self.s.panel(state).state, Panel.MENU)

    def test_dvs(self):
        self.start(*h.OPEN_EDITOR, *press(RIGHT), *press("A"))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.col, state.row), (EditState.ADJUST, EditState.COL_DV, 1))
        screens.check(self, "hints_adjust", self.s.shot("hints_adjust"), screens.SIDEBAR)

        # Attack: both ends, single steps, steps of four, and no step past an end.
        for button, dvs in (("R", 0xFAA9), ("L", 0x0AA9), (UP, 0x1AA9), (RIGHT, 0x5AA9), (LEFT, 0x1AA9),
                            (DOWN, 0x0AA9), (DOWN, 0x0AA9), (LEFT, 0x0AA9)):
            self.do(*press(button))
            record = self.s.record()
            self.assertEqual(record.dvs, dvs, button)
            self.assertStatsFollow(record)

        self.do(*press("A"), *press(DOWN), *press("A"), *press("R"), *press("A"))
        state = self.s.edit_state()
        record = self.s.record()
        self.assertEqual((state.mode, state.row), (EditState.FIELDS, 2))
        self.assertEqual(record.dvs, 0x0FA9)
        self.assertStatsFollow(record)

    def test_hp_dv_cannot_be_selected(self):
        # Right from the first move lands on Attack, the first DV that can be changed.
        self.start(*h.OPEN_EDITOR, *press(RIGHT), *press(UP))
        state = self.s.edit_state()
        self.assertEqual((state.col, state.row, state.on_name), (EditState.COL_DV, 1, 1))   # up went to the name

    def test_stat_exp_moves_between_the_values_that_matter(self):
        self.start(*h.OPEN_EDITOR, *presses(RIGHT, 2), *press(UP), *press("A"))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.col, state.row), (EditState.ADJUST, EditState.COL_STAT_EXP, 0))

        def tier(n):
            return (4 * n - 1) ** 2 + 1

        for button, value in (("L", 0), (DOWN, 0), (UP, tier(1)), (UP, tier(2)), (RIGHT, tier(10)), ("R", 65535),
                              (UP, 65535), (DOWN, tier(62)), (LEFT, tier(54))):
            self.do(*press(button))
            record = self.s.record()
            self.assertEqual(record.stat_exp, [value] + [45000] * 4, button)
            self.assertStatsFollow(record)

    def test_every_stat_exp_step_changes_the_stat(self):
        self.start(*h.OPEN_EDITOR, *presses(RIGHT, 2), *press("A"), *press("L"))
        attack = [self.s.record().stats[1]]
        for _ in range(6):
            self.do(*press(UP))
            attack.append(self.s.record().stats[1])
        self.assertEqual(attack, sorted(set(attack)))   # strictly rising

    def test_level(self):
        self.start(*h.OPEN_EDITOR, *presses(DOWN, 4), *press("A"))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.col, state.row), (EditState.ADJUST, EditState.COL_MOVES, 4))

        for button, level in (("L", 2), (DOWN, 2), (UP, 3), (RIGHT, 13), ("R", 100), (UP, 100), (LEFT, 90)):
            self.do(*press(button))
            record = self.s.record()
            self.assertEqual(record.level, level, button)
            self.assertEqual(record.exp, h.medium_slow_exp(level))
            self.assertStatsFollow(record)

    def test_happiness(self):
        self.start(*h.OPEN_EDITOR, *presses(DOWN, 4), *press(RIGHT))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.col, state.row), (EditState.FIELDS, EditState.COL_HAPPINESS, 4))
        before = self.s.record()
        self.assertEqual(before.happiness, 128)

        # Both ends, single steps, steps of 25, and no step past an end.
        self.do(*press("A"))
        self.assertEqual(self.s.edit_state().mode, EditState.ADJUST)
        for button, happiness in (("R", 255), (UP, 255), ("L", 0), (DOWN, 0), (UP, 1), (RIGHT, 26), (LEFT, 1),
                                  (LEFT, 0), ("R", 255), (LEFT, 230)):
            self.do(*press(button))
            self.assertEqual(self.s.record().happiness, happiness, button)

        # Nothing else in the record moved. The title row shows Return at 92 and Frustration at 10.
        record = self.s.record()
        self.assertEqual(record.data[:0x1C] + record.data[0x1D:], before.data[:0x1C] + before.data[0x1D:])
        screens.check(self, "fields_happiness", self.s.shot("fields_happiness"))

    def test_happiness_is_a_field_of_the_levels_row_only(self):
        self.start(*h.OPEN_EDITOR, *press(DOWN))

        def cursor():
            state = self.s.edit_state()
            return state.col, state.row

        # Sideways from a move the cursor passes over it, both ways.
        for button, where in ((RIGHT, (EditState.COL_DV, 1)), (LEFT, (EditState.COL_MOVES, 1))):
            self.do(*press(button))
            self.assertEqual(cursor(), where, button)

        # From the level it is the next field along; up from it leads back to the moves.
        self.do(*presses(DOWN, 3))
        for button, where in ((RIGHT, (EditState.COL_HAPPINESS, 4)), (RIGHT, (EditState.COL_DV, 4)),
                              (LEFT, (EditState.COL_HAPPINESS, 4)), (DOWN, (EditState.COL_HAPPINESS, 4)),
                              (UP, (EditState.COL_MOVES, 3)), (DOWN, (EditState.COL_MOVES, 4))):
            self.do(*press(button))
            self.assertEqual(cursor(), where, button)

    def test_move_list_offers_exactly_the_legal_moves(self):
        self.start(*h.OPEN_EDITOR, *press("A", 20))
        state = self.s.edit_state()
        entries = [0] + h.legal_moves(h.ABRA)   # 0 removes the move
        self.assertEqual(state.mode, EditState.MOVE_LIST)
        self.assertEqual(state.list, entries)
        self.assertEqual(state.cursor, entries.index(h.PSYCHIC))

    def test_picking_a_move(self):
        self.start(*h.OPEN_EDITOR, *press("A", 20))
        before = self.s.record()
        entries = [0] + h.legal_moves(h.ABRA)
        new = next(move for move in entries[1:] if move not in before.moves)
        self.assertEqual(before.pp[0] & 0xC0, 0, "the checks below assume no PP Ups")

        self.do(*to_list_entry(entries.index(new), self.s.edit_state().cursor), *press("A", 20))
        record = self.s.record()
        self.assertEqual(self.s.edit_state().mode, EditState.FIELDS)
        self.assertEqual(record.moves, [new] + before.moves[1:])
        self.assertEqual(record.pp, [h.base_pp(new)] + before.pp[1:])

        # A move the Pokemon already knows in another slot is refused.
        self.do(*press("A", 20))
        cursor = self.s.edit_state().cursor
        self.assertEqual(cursor, entries.index(new))
        self.do(*to_list_entry(entries.index(h.ICE_PUNCH), cursor), *press("A", 20))
        self.assertEqual(self.s.edit_state().mode, EditState.MOVE_LIST)
        self.assertEqual(self.s.record().moves, record.moves)

        self.do(*press("B", 20))
        self.assertEqual(self.s.edit_state().mode, EditState.FIELDS)
        self.assertEqual(self.s.record().data, record.data)

    def test_scroll_bar_follows_the_move_list(self):
        self.start(*h.OPEN_EDITOR, *press("A", 20))
        state = self.s.edit_state()
        last_top = state.count - LIST_PAGE   # the first row showing when the list is at its end

        # It opens where the list does, part of the way down with the Pokemon's move in view.
        self.assertTrue(0 < state.top < last_top)
        self.assertEqual(state.scroll, state.top * EditState.SCROLL_UNITS // last_top)

        # The knob glides to where the list has gone, so give it time to arrive.
        self.do(*press(RIGHT, 40))
        state = self.s.edit_state()
        self.assertTrue(0 < state.top < last_top)
        self.assertEqual(state.scroll, state.top * EditState.SCROLL_UNITS // last_top)

        self.do(*presses(RIGHT, state.count // LIST_PAGE), "wait 40")
        state = self.s.edit_state()
        self.assertEqual((state.cursor, state.top, state.scroll),
                         (state.count - 1, last_top, EditState.SCROLL_UNITS))
        shot = self.s.shot("list_end")
        screens.check(self, "list_end", shot)
        screens.check(self, "hints_list", shot, screens.SIDEBAR)

        self.do(*presses(LEFT, state.count // LIST_PAGE + 1), "wait 40")
        state = self.s.edit_state()
        self.assertEqual((state.cursor, state.top, state.scroll), (0, 0, 0))

    def test_removing_and_adding_moves(self):
        self.start(*h.OPEN_EDITOR)
        moves, pp = self.s.record().moves, self.s.record().pp
        for left in (3, 2, 1):
            self.do(*press("A", 20))
            self.do(*to_list_entry(0, self.s.edit_state().cursor), *press("A", 20))
            record = self.s.record()
            self.assertEqual(record.moves, moves[4 - left:] + [0] * (4 - left))
            self.assertEqual(record.pp, pp[4 - left:] + [0] * (4 - left))

        # The last move cannot be removed: its list has no such entry.
        self.do(*press("A", 20))
        state = self.s.edit_state()
        legal = h.legal_moves(h.ABRA)
        self.assertEqual(state.list, legal)
        self.do(*press("B", 20))

        # One empty slot is offered below the moves; the rows after it are skipped.
        self.do(*press(DOWN))
        self.assertEqual(self.s.edit_state().row, 1)
        self.do(*press(DOWN))
        self.assertEqual(self.s.edit_state().row, 4)
        self.do(*press(UP), *press("A", 20))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.row, state.list, state.cursor), (EditState.MOVE_LIST, 1, legal, 0))

        new = next(move for move in legal if move != moves[3])
        self.do(*to_list_entry(legal.index(new), 0), *press("A", 20))
        record = self.s.record()
        self.assertEqual(record.moves, [moves[3], new, 0, 0])
        self.assertEqual(record.pp[1], h.base_pp(new))

    def test_shiny_dvs_reload_the_model_and_icon(self):
        self.start(*h.OPEN_EDITOR)
        cell = self.s.panel().pokemon
        icon = self.s.read(cell + h.CELL_ICON, h.ICON_SIZE)
        colour = screens.region_mean(self.s.shot("model_plain"), screens.MODEL)

        # Attack and Special from 9 to 10; Defense and Speed are 10 already.
        self.do(*press(RIGHT), *press("A"), *press(UP), *press("A"),
                *presses(DOWN, 3), *press("A"), *press(UP), *press("A"), "wait 30")
        self.assertEqual(self.s.record().dvs, 0xAAAA)
        self.assertEqual(self.s.panel().model_timer, 0)
        self.assertNotEqual(self.s.read(cell + h.CELL_ICON, h.ICON_SIZE), icon)

        shot = self.s.shot("fields_shiny")
        shiny = screens.region_mean(shot, screens.MODEL)
        self.assertGreater(sum(abs(a - b) for a, b in zip(colour, shiny)), 8,   # 16 when it works, 1 when not
                           f"the model did not change colour: {colour} then {shiny}")
        screens.check(self, "fields_shiny", shot)

    def test_hidden_power_shows_its_real_type_and_power(self):
        self.start(*h.OPEN_EDITOR, *press("A", 20))
        entries = [0] + h.legal_moves(h.ABRA)
        self.do(*to_list_entry(entries.index(h.HIDDEN_POWER), self.s.edit_state().cursor), *press("A", 20))
        self.assertEqual(self.s.record().moves[0], h.HIDDEN_POWER)
        screens.check(self, "fields_hidden_power", self.s.shot("fields_hidden_power"))

        self.do(*press("A", 20))
        screens.check(self, "list_hidden_power", self.s.shot("list_hidden_power"))

    def test_typing_a_name(self):
        self.start(*h.OPEN_EDITOR, *press(UP))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.on_name, state.col, state.row), (EditState.FIELDS, 1, 0, 0))
        self.do(*press(DOWN))
        self.assertEqual(self.s.edit_state().on_name, 0)

        self.do(*press(UP), *press("A", 20))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.name, state.name_length), (EditState.NAME, b"ABRA", 4))
        self.assertEqual((state.key_page, state.key_col, state.key_row), (0, 0, 0))
        shot = self.s.shot("keyboard_upper")
        screens.check(self, "keyboard_upper", shot)
        screens.check(self, "hints_keyboard", shot, screens.SIDEBAR)

        # Clear it, then Z, z and the PK sign from the lower page, and the female sign.
        self.do(*presses("B", 4))
        self.assertEqual(self.s.edit_state().name, b"")
        self.do(*presses(DOWN, 2), *presses(RIGHT, 7), *press("A"), *press("R"), *press("A"),
                *press(DOWN), *press("A"))
        state = self.s.edit_state()
        self.assertEqual((state.name, state.key_page, state.key_col, state.key_row), (b"Zz\xBC", 1, 7, 3))
        screens.check(self, "keyboard_lower", self.s.shot("keyboard_lower"))

        self.do(*press("L"), *press("A"), *press("Start"))
        state = self.s.edit_state()
        self.assertEqual((state.name, state.key_page, state.key_col, state.key_row),
                         (b"Zz\xBC\xBE", 0, END_COLUMN, KEY_ROW_WIDE))

        self.do(*press("A", 20))
        self.assertEqual(self.s.edit_state().mode, EditState.FIELDS)
        self.assertEqual(self.s.record().nickname, b"Zz\xBC\xBE")

    def test_name_length_and_empty_names(self):
        self.start(*h.OPEN_EDITOR, *press(UP), *press("A", 20), *presses("A", 6))
        state = self.s.edit_state()
        self.assertEqual((state.name, state.name_length), (b"ABRAAAAAAA", 10))
        self.assertEqual((state.key_col, state.key_row), (END_COLUMN, KEY_ROW_WIDE))   # a full name jumps to END

        # An eleventh character is refused.
        self.do(*press(UP), *press("A"))
        self.assertEqual(self.s.edit_state().name, b"ABRAAAAAAA")
        self.do(*press("Start"), *press("A", 20))
        self.assertEqual(self.s.record().nickname, b"ABRAAAAAAA")

        # B deletes; with nothing left it backs out and the name is kept.
        self.do(*press("A", 20), *presses("B", 10))
        state = self.s.edit_state()
        self.assertEqual((state.mode, state.name_length), (EditState.NAME, 0))
        self.do(*press("B", 20))
        self.assertEqual(self.s.edit_state().mode, EditState.FIELDS)
        self.assertEqual(self.s.record().nickname, b"ABRAAAAAAA")

        # END on an empty name gives the species name back.
        self.do(*press("A", 20), *presses("B", 10), *press("Start"), *press("A", 20))
        self.assertEqual(self.s.edit_state().mode, EditState.FIELDS)
        self.assertEqual(self.s.record().nickname, b"ABRA")

    def test_keyboard_cursor_wraps(self):
        self.start(*h.OPEN_EDITOR, *press(UP), *press("A", 20))

        def key():
            state = self.s.edit_state()
            return state.key_col, state.key_row

        for button, where in ((LEFT, (8, 0)), (RIGHT, (0, 0)), (UP, (0, KEY_ROW_WIDE)),
                              (LEFT, (END_COLUMN, KEY_ROW_WIDE)),   # off the left of lower/UPPER, onto END
                              (RIGHT, (1, KEY_ROW_WIDE)),           # and back round
                              (DOWN, (1, 0)), (UP, (1, KEY_ROW_WIDE))):
            self.do(*press(button))
            self.assertEqual(key(), where, button)

        # The wide keys: lower/UPPER switches page, DEL deletes.
        self.do(*press("A"))
        self.assertEqual(self.s.edit_state().key_page, 1)
        self.do(*press("A"))
        self.assertEqual(self.s.edit_state().key_page, 0)
        self.do(*press(RIGHT), *press("A"))
        self.assertEqual(self.s.edit_state().name, b"ABR")

    def test_renaming_tints_the_icon_and_the_species_name_clears_it(self):
        # The game tints a Pokemon whose nickname is not its species name.
        self.start(*h.OPEN_EDITOR)
        cell = self.s.panel().pokemon
        icon = self.s.read(cell + h.CELL_ICON, h.ICON_SIZE)

        self.do(*press(UP), *press("A", 20), *press("A"), *press("Start"), *press("A", 40))
        self.assertEqual(self.s.record().nickname, b"ABRAA")
        self.assertNotEqual(self.s.read(cell + h.CELL_ICON, h.ICON_SIZE), icon)

        self.do(*press("A", 20), *presses("B", 5), *press("Start"), *press("A", 40))
        self.assertEqual(self.s.record().nickname, b"ABRA")
        self.assertEqual(self.s.read(cell + h.CELL_ICON, h.ICON_SIZE), icon)


if __name__ == "__main__":
    unittest.main()
