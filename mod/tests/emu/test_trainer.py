"""Change Trainer: the entry in the menu a chosen team gets, its window, and what follows.

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import unittest

import harness as h
import screens
from harness import DOWN, LEFT, RIGHT, UP, EditState, Menu, TrainerState, press, presses

STOCK_ENTRIES = 5    # OK, OK to Register, Reselect some, Reselect all, Change Item
MOD_ENTRIES = 2      # Edit POKeMON, Change Trainer
LAST = h.NUM_TRAINERS - 1   # the last trainer, and the one before the game's own in the ring
CAL = (0x14, 2)      # the first opponent of Free Battle, as the game pictures him
C_LEFT, C_RIGHT = "C Left", "C Right"
NUMBERS = h.picture_numbers() if h.AVAILABLE else []
GYM_LEADER, RIVAL = 0x28, 0x2A   # titles, by number; the last two the window steps through
# From the entry screen with the team menu on OK: OK, then the COM's team the same way,
# which leads to the opponent's introduction. That screen loads both sides' pictures for
# itself, and as it ends decides the ones the screens after it show.
TO_INTRO = press("A", 240) + h.RENTAL_ONLY + h.ENTER_FIRST + ["wait 160"]
TO_VERSUS = press("A", 100)
TO_ORDER_SCREEN = ["wait 260"]
# From the order screen into the battle, and straight out of it again by Start and Yes,
# to the result, which is the introduction's screen in its other mode.
TO_RESULT = (press("A", 300) + press("B", 60) + press("A", 120) + press("A", 1300)
             + press("Start", 60) + press(RIGHT, 20) + press("A", 60) + presses("A", 2, 90))
INTRO, RESULT = 0, 1
YOU = h.trainer_picture(*h.DEFAULT_PICTURE)
# In the window, from the picture: down to the name, the keyboard, A then S then H, and END.
# That leaves the window on the name, where A would type again.
TYPE_ASH = (press(DOWN) + press("A", 20) + press("A") + presses(DOWN, 2) + press("A")
            + presses(UP, 2) + presses(RIGHT, 7) + press("A") + press("Start") + press("A", 20))


def picture_for(choice: int) -> bytes:
    """What the window shows for a choice: the game's own, or the picture of that number."""
    return h.trainer_picture(*(h.DEFAULT_PICTURE if choice == 0 else NUMBERS[choice - 1]))


def shown(trainer: int, face: int = None) -> int:
    """The choice a trainer's picture is; without `face`, the one the window shows first."""
    return h.picture_choice(trainer, face)


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class TrainerTest(h.EmulatorTest):
    def assertShows(self, choice: int) -> None:
        state = self.s.trainer_state()
        self.assertEqual(state.choice, choice)
        # The window knows whose picture it is and which of theirs: 0 for the game's own.
        whose = (0, 0) if choice == 0 else (NUMBERS[choice - 1][0] + 1, NUMBERS[choice - 1][1])
        self.assertEqual((state.trainer, state.face), whose)
        self.assertEqual(self.s.trainer_picture(), picture_for(choice), f"choice {choice}")

    def test_team_menu_has_one_more_entry(self):
        self.start(*h.TEAM_MENU)
        menu = self.s.team_menu()
        self.assertEqual((menu.status, menu.count, menu.cursor), (Menu.OPEN, STOCK_ENTRIES + MOD_ENTRIES, 0))
        screens.check(self, "team_menu", self.s.shot("team_menu"), screens.TEAM_MENU)

        # The stock entries still do what they did: OK goes on to the COM's team, whose
        # menu has Edit POKeMON but no Change Trainer, there being no player behind it.
        self.do(*press("A", 240), *h.RENTAL_ONLY, *h.TEAM_MENU)
        menu = self.s.team_menu()
        self.assertEqual((menu.status, menu.count), (Menu.OPEN, STOCK_ENTRIES + 1))
        self.do(*h.EDIT_POKEMON, *h.OPEN_MEMBER)
        self.assertEqual((self.s.edit_state().mode, self.s.panel().pokemon), (EditState.FIELDS, self.s.party_cell()))

    def test_window_steps_round_every_picture(self):
        self.start(*h.OPEN_TRAINER)
        state = self.s.trainer_state()
        self.assertEqual((state.open, state.controller, state.port, state.row), (1, 0, 0, TrainerState.ROW_PICTURE))
        self.assertEqual((state.name, state.title_text), (b"", b"POK\xe9MON TRAINER"))
        self.assertEqual(self.s.team_menu().status, Menu.CLOSED)
        self.assertShows(0)
        screens.check(self, "trainer_window", self.s.shot("trainer_window"), screens.TRAINER)

        # Left and Right go round the trainers, each on the picture the window shows first.
        for button, choice in ((LEFT, shown(LAST)), (RIGHT, 0), (RIGHT, shown(0)), (RIGHT, shown(1)),
                               (LEFT, shown(0))):
            self.do(*press(button))
            self.assertShows(choice)
        self.assertEqual(self.s.trainer_choices(), [0, 0, 0, 0], "nothing is kept before A")

    def test_c_buttons_go_round_a_trainers_pictures(self):
        # The game's own choice is one picture, so there is nothing to go round.
        self.start(*h.OPEN_TRAINER, *press(C_RIGHT), *press(C_LEFT))
        self.assertShows(0)

        # The first trainer has three, and the window starts on the second.
        self.assertEqual(h.trainer_faces(0), (3, 1))
        self.do(*press(RIGHT))
        self.assertShows(shown(0, 1))
        screens.check(self, "trainer_faces", self.s.shot("trainer_faces"), screens.TRAINER)
        for button, face in ((C_RIGHT, 2), (C_RIGHT, 0), (C_LEFT, 2), (C_LEFT, 1), (C_LEFT, 0)):
            self.do(*press(button))
            self.assertShows(shown(0, face))

        # They do the same with the cursor on the name or the title, and move nothing else.
        self.do(*press(DOWN), *press(C_RIGHT))
        self.assertShows(shown(0, 1))
        self.do(*press(DOWN), *press(C_RIGHT))
        self.assertShows(shown(0, 2))
        state = self.s.trainer_state()
        self.assertEqual((state.row, state.title_text), (TrainerState.ROW_TITLE, b"POK\xe9MON TRAINER"))

        # A trainer with one picture: the sixth.
        self.assertEqual(h.trainer_faces(5), (1, 0))
        self.do(*press(DOWN), *presses(RIGHT, 5), *press(C_RIGHT), *press(C_LEFT))
        self.assertShows(shown(5))
        self.assertEqual(self.s.trainer_choices(), [0, 0, 0, 0], "nothing is kept before A")

    def test_every_picture_of_every_trainer_can_be_chosen(self):
        self.start(*h.OPEN_TRAINER)
        base, _ = self.s.fragment(h.MOD_VRAM)
        state = base + self.s.trainer_offset
        # Round the whole ring, and at each trainer round all of its pictures: what the
        # window holds after every press, read in one go.
        look = [f"read {state + 3:08X} 1", f"read {state + TrainerState.PICTURE:08X} {h.PICTURE_BYTES}"]
        commands, expected = [], []
        for trainer in range(h.NUM_TRAINERS):
            count, first = h.trainer_faces(trainer)
            commands += press(RIGHT) + look
            expected.append(shown(trainer, first))
            for step in range(1, count + 1):
                commands += press(C_RIGHT) + look
                expected.append(shown(trainer, (first + step) % count))
        data = bytes.fromhex("".join(line.split(":", 1)[1] for line in self.s.run(*commands)))
        size = 1 + h.PICTURE_BYTES
        self.assertEqual(len(data), size * len(expected))
        for index, choice in enumerate(expected):
            held = data[index * size:(index + 1) * size]
            self.assertEqual(held[0], choice, index)
            self.assertEqual(held[1:], picture_for(choice), f"choice {choice}")
        self.assertEqual(sorted(set(expected)), list(range(1, len(NUMBERS) + 1)), "every number was shown")

    def test_rows_and_titles_go_round(self):
        self.start(*h.OPEN_TRAINER)
        for button, row in ((UP, TrainerState.ROW_TITLE), (UP, TrainerState.ROW_NAME), (DOWN, TrainerState.ROW_TITLE),
                            (DOWN, TrainerState.ROW_PICTURE), (DOWN, TrainerState.ROW_NAME)):
            self.do(*press(button))
            self.assertEqual(self.s.trainer_state().row, row, button)

        # Sideways does nothing to a name, and on the title steps through the game's own.
        self.do(*press(RIGHT), *press(DOWN))
        self.assertShows(0)
        for button, title in ((LEFT, b"RIVAL"), (LEFT, b"GYM LEADER"), (RIGHT, b"RIVAL"),
                              (RIGHT, b"POK\xe9MON TRAINER"), (RIGHT, b"MEDIUM")):
            self.do(*press(button))
            self.assertEqual(self.s.trainer_state().title_text, title, button)

    def test_b_leaves_everything_as_it_was(self):
        self.start(*h.OPEN_TRAINER, *presses(RIGHT, 3), *TYPE_ASH, *press(DOWN), *press(LEFT), *press("B", 40))
        self.assertEqual(self.s.trainer_state().open, 0)
        self.assertEqual((self.s.trainer_choices(), self.s.trainer_titles(), self.s.trainer_names()),
                         ([0] * 4, [h.PLAYER_TITLE] * 4, [b""] * 4))
        self.assertEqual(self.s.party_name(), b"")
        # The menu is back, on OK.
        menu = self.s.team_menu()
        self.assertEqual((menu.status, menu.count, menu.cursor), (Menu.OPEN, STOCK_ENTRIES + MOD_ENTRIES, 0))

        self.do(*h.CHANGE_TRAINER)
        self.assertShows(0)
        state = self.s.trainer_state()
        self.assertEqual((state.name, state.title_text), (b"", b"POK\xe9MON TRAINER"))

    def test_a_chosen_picture_is_remembered_and_used(self):
        # The last trainer's second picture, which is not the one the window starts on,
        # and whose number is past what a signed byte holds.
        self.start(*h.OPEN_TRAINER, *press(LEFT), *press(C_LEFT), *press("A", 40))
        choice = shown(LAST, 1)
        self.assertNotEqual(choice, shown(LAST))
        self.assertGreater(choice - 1, 0x7F)
        self.assertEqual(self.s.trainer_state().open, 0)
        self.assertEqual(self.s.trainer_choices(), [choice, 0, 0, 0])

        # The window opens on it the next time.
        self.do(*h.CHANGE_TRAINER)
        self.assertShows(choice)
        self.do(*press("B", 40))

        # It is the player's picture on every screen from here to the battle: first where
        # the two sides are set against each other, once the opponent has had his say.
        self.do(*TO_INTRO)
        self.assertEqual(self.s.fragment(h.MOD_VRAM), (0, 0), "the mod is still loaded")
        mode, pictures = self.s.intro()
        self.assertEqual(mode, INTRO)
        self.assertEqual(pictures[0], picture_for(choice))
        self.do(*TO_VERSUS)
        screens.check(self, "versus", self.s.shot("versus"), screens.VERSUS)

        # Then on the order screen, where the COM keeps its own.
        self.do(*TO_ORDER_SCREEN)
        self.assertEqual(self.s.battle_pictures(), [(choice - 1, 0), CAL])

        # And after the battle, on the result and on the way into the next one.
        self.do(*TO_RESULT)
        mode, pictures = self.s.intro()
        self.assertEqual(mode, RESULT)
        self.assertEqual(pictures[0], picture_for(choice))
        self.assertEqual(self.s.trainer_choices(), [choice, 0, 0, 0])

    def test_a_name_and_title_are_remembered_and_used(self):
        self.start(*h.OPEN_TRAINER, *press(DOWN), *press("A", 20))
        self.assertEqual(self.s.trainer_state().typing, 1)
        screens.check(self, "trainer_keyboard", self.s.shot("trainer_keyboard"))

        # B with nothing typed goes back; then the name for real, and a title.
        self.do(*press("B", 20), *press(UP), *TYPE_ASH, *press(DOWN), *presses(LEFT, 2))
        state = self.s.trainer_state()
        self.assertEqual((state.typing, state.row, state.name, state.title_text),
                         (0, TrainerState.ROW_TITLE, b"ASH", b"GYM LEADER"))
        self.assertEqual(self.s.trainer_names(), [b""] * 4, "nothing is kept before A")
        screens.check(self, "trainer_named", self.s.shot("trainer_named"), screens.TRAINER)

        self.do(*press("A", 40))
        self.assertEqual(self.s.trainer_names(), [b"ASH", b"", b"", b""])
        self.assertEqual(self.s.trainer_titles(), [GYM_LEADER] + [h.PLAYER_TITLE] * 3)
        self.assertEqual(self.s.party_name(), b"ASH")

        # They are the player's on the screens that follow, with the COM's untouched.
        self.do(*TO_INTRO)
        self.assertEqual(self.s.battle_names(), [b"ASH", b"CAL"])
        self.do(*TO_VERSUS)
        screens.check(self, "versus_named", self.s.shot("versus_named"), screens.VERSUS_LABEL)
        self.do(*TO_ORDER_SCREEN, *TO_RESULT)
        self.assertEqual(self.s.intro()[0], RESULT)
        self.assertEqual(self.s.battle_names(), [b"ASH", b"CAL"])
        # The result looks its title up for itself, and only the picture says which it
        # found. After a battle that is the picture as the game drew it; see screens.py.
        shot = self.s.shot("result_named")
        screens.check_drawn(self, "result_named", self.s.drawn(screens.VERSUS_LABEL), shot)

    def test_a_name_can_be_taken_back(self):
        self.start(*h.OPEN_TRAINER, *TYPE_ASH, *press(DOWN), *press("A", 40))
        self.assertEqual((self.s.trainer_names()[0], self.s.party_name()), (b"ASH", b"ASH"))

        # The window has the name; END on an empty one gives the game's back.
        self.do(*h.CHANGE_TRAINER)
        self.assertEqual(self.s.trainer_state().name, b"ASH")
        self.do(*press(DOWN), *press("A", 20), *presses("B", 3), *press("Start"), *press("A", 20), *press(DOWN),
                *press("A", 40))
        self.assertEqual((self.s.trainer_names()[0], self.s.party_name()), (b"", b""))
        self.do(*TO_INTRO)
        self.assertEqual(self.s.battle_names(), [b"1P", b"CAL"])

    def test_a_remembered_name_is_given_on_the_next_visit(self):
        # As if kept on an earlier visit to the entry screen: put there before this one.
        self.do("player 1", "load map", "wait 20", f"write {h.TRAINER_NAMES:08X} 52454400", *h.SCENES["picker"],
                *h.TEAM_MENU)
        self.assertEqual(self.s.party_name(), b"RED")
        self.do(*TO_INTRO)
        self.assertEqual(self.s.battle_names(), [b"RED", b"CAL"])

    def test_a_remembered_name_is_used_where_no_team_is_chosen(self):
        # The Challenge Cup deals the teams itself, so no entry screen hands a name on.
        # Without one kept the player is 1P, as in the game.
        self.do("player 1", "load map", "wait 20", *h.CHALLENGE_CUP)
        self.assertEqual(self.s.fragment(h.PICKER_VRAM), (0, 0), "there was an entry screen")
        self.assertEqual(self.s.battle_names(), [b"1P", b"CAL"])

        # With one kept on an earlier visit to an entry screen, the player has it here too.
        self.do("player 1", "load map", "wait 20", f"write {h.TRAINER_NAMES:08X} 52454400", *h.CHALLENGE_CUP)
        self.assertEqual(self.s.battle_names(), [b"RED", b"CAL"])
        self.do("wait 160", *TO_VERSUS)
        screens.check(self, "versus_challenge", self.s.shot("versus_challenge"), screens.VERSUS_LABEL)
        self.do(*TO_ORDER_SCREEN)
        self.assertEqual(self.s.battle_names(), [b"RED", b"CAL"])

    def test_without_a_choice_the_game_decides_as_before(self):
        self.start(*h.ENTER_FIRST, *h.RENTAL_ONLY, *h.ENTER_FIRST, "wait 160")
        mode, pictures = self.s.intro()
        self.assertEqual((mode, pictures), (INTRO, [YOU, YOU]))   # the second is loaded and not shown
        self.assertEqual(self.s.battle_names(), [b"1P", b"CAL"])
        self.do(*TO_VERSUS)
        screens.check(self, "versus_plain", self.s.shot("versus_plain"), screens.VERSUS_LABEL)
        self.do(*TO_ORDER_SCREEN)
        self.assertEqual(self.s.battle_pictures(), [h.DEFAULT_PICTURE, CAL])
        self.do(*TO_RESULT)
        self.assertEqual(self.s.intro(), (RESULT, [YOU, YOU]))

    def test_nothing_outlasts_the_power(self):
        self.start(*h.OPEN_TRAINER, *press(RIGHT), *TYPE_ASH, *press(DOWN), *press(LEFT), *press("A", 40))
        self.assertEqual((self.s.trainer_choices(), self.s.trainer_titles()[0], self.s.trainer_names()[0]),
                         ([shown(0), 0, 0, 0], RIVAL, b"ASH"))
        self.s.reboot()
        self.assertEqual((self.s.trainer_choices(), self.s.trainer_titles(), self.s.trainer_names()),
                         ([0] * 4, [h.PLAYER_TITLE] * 4, [b""] * 4))


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class TwoPlayerTrainerTest(h.EmulatorTest):
    scene = "two"

    def test_each_player_chooses_their_own(self):
        self.start("player 2", *h.OPEN_TRAINER)
        state = self.s.trainer_state()
        self.assertEqual((state.open, state.controller, state.port), (1, 1, 1))

        # Controller 1 has no say in it, in the window or on the keyboard.
        everything = press(RIGHT) + press(C_RIGHT) + press(DOWN) + press("A") + press("B") + press("Start")
        self.do("player 1", *everything)
        state = self.s.trainer_state()
        self.assertEqual((state.open, state.choice, state.row), (1, 0, TrainerState.ROW_PICTURE))
        self.do("player 2", *press(DOWN), *press("A", 20), "player 1", *everything)
        state = self.s.trainer_state()
        self.assertEqual((state.typing, state.name), (1, b""))

        self.do("player 2", *press("B", 20), *press(UP), *presses(RIGHT, 2), *press(C_RIGHT), *TYPE_ASH,
                *press(DOWN), *press("A", 40))
        choice = shown(1, 0)
        self.assertEqual(h.trainer_faces(1), (3, 2))
        self.assertEqual(self.s.trainer_choices(), [0, choice, 0, 0])
        self.assertEqual(self.s.trainer_names(), [b"", b"ASH", b"", b""])

        # Player 1 left theirs alone and keeps the game's; player 2 has trainer 1 and a name.
        self.do(*press("A", 240), "player 1", "wait 160")
        self.assertEqual(self.s.intro(), (INTRO, [YOU, picture_for(choice)]))
        self.assertEqual(self.s.battle_names(), [b"1P", b"ASH"])
        self.do(*press("A", 360))
        self.assertEqual(self.s.battle_pictures(), [h.DEFAULT_PICTURE, (choice - 1, 0)])


if __name__ == "__main__":
    unittest.main()
