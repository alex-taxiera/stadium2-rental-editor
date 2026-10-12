"""What the mod assumes about the ROM's trainer pictures and titles, and about where it
remembers a player's. Run: python3 -m unittest discover mod/tests"""

import re
import struct
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import gen_trainer_titles  # noqa: E402

BASE_ROM = REPO_ROOT / "baseroms" / "us" / "baserom.z64"
GAME_H = REPO_ROOT / "mod" / "include" / "game.h"
TRAINER_H = REPO_ROOT / "mod" / "include" / "trainer.h"
STOCK_PATCHES = REPO_ROOT / "mod" / "stock_patches.txt"
NMI_BUFFER, NMI_BUFFER_SIZE = 0x8000031C, 0x40   # osAppNMIBuffer


def address(name: str) -> int:
    """A fixed address mod/include/game.h gives a name to."""
    return int(re.search(rf"^#define {name} \(\(\w+ \*\)(\w+)\)", GAME_H.read_text(encoding="utf-8"), re.M).group(1), 16)


def constant(name: str) -> int:
    """A #define of mod/include/game.h."""
    return int(re.search(rf"^#define {name} (\w+)", GAME_H.read_text(encoding="utf-8"), re.M).group(1), 0)


@unittest.skipUnless(BASE_ROM.exists(), "no baserom; run tools/mod/check_rom.py")
class TrainerPicturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = BASE_ROM.read_bytes()
        cls.base = constant("TRAINER_PICTURES_ROM")
        cls.count, = struct.unpack_from(">I", cls.rom, cls.base + 0xC)

    def expressions(self, trainer: int) -> list:
        """Where in the ROM each expression of a trainer starts, header included."""
        entry = self.base + struct.unpack_from(">I", self.rom, self.base + 0x10 + trainer * 0x10)[0]
        count, = struct.unpack_from(">I", self.rom, entry)
        return [entry + offset - 8 for offset in struct.unpack_from(f">{count}I", self.rom, entry + 4)]

    def test_the_archive_has_as_many_trainers_as_the_window_steps_through(self):
        self.assertEqual(self.count, constant("NUM_TRAINER_PICTURES"))
        self.assertLess(self.count, 0x80)   # the game keeps a trainer's number in a signed byte

    def test_every_trainer_has_a_first_expression_of_the_size_the_window_draws(self):
        size, total = constant("TRAINER_PICTURE_SIZE"), constant("TRAINER_PICTURE_BYTES")
        self.assertEqual(total, 8 + size * size * 2)
        starts = []
        for trainer in range(self.count):
            expressions = self.expressions(trainer)
            self.assertIn(len(expressions), (1, 2, 3), trainer)
            for start in expressions:
                self.assertEqual(struct.unpack_from(">HHH", self.rom, start), (size, size, 2), trainer)
            starts += expressions
        # Pictures do not overlap, so each read of `total` bytes is one whole picture.
        starts.sort()
        self.assertTrue(all(b - a >= total for a, b in zip(starts, starts[1:])))

    def test_the_games_own_picture_is_there(self):
        trainer, expression = constant("DEFAULT_TRAINER_PICTURE"), constant("DEFAULT_TRAINER_EXPRESSION")
        self.assertLess(trainer, self.count)
        self.assertLess(expression, len(self.expressions(trainer)))

    def test_the_choices_are_kept_in_the_buffer_the_os_clears_at_power_on(self):
        choices = address("gTrainerChoices")
        self.assertEqual(choices + 4, NMI_BUFFER + NMI_BUFFER_SIZE)
        # The patched stock code reads the same bytes.
        loads = re.findall(r"lbu\s+\$t\d, (\w+)\(\$t\d\)\s*$", STOCK_PATCHES.read_text(encoding="utf-8"), re.M)
        self.assertEqual(len(loads), 3)
        self.assertEqual({0x80000000 + int(load, 16) for load in loads}, {choices})


class TrainerMemoryTest(unittest.TestCase):
    def test_names_titles_and_choices_share_the_buffer_without_overlapping(self):
        names, titles, choices = address("gTrainerNames"), address("gTrainerTitles"), address("gTrainerChoices")
        name_bytes = constant("TRAINER_NAME_BYTES")
        self.assertEqual(name_bytes, constant("MAX_TRAINER_NAME") + 1)
        self.assertGreaterEqual(names, NMI_BUFFER)
        self.assertEqual(names + 4 * name_bytes, titles)
        self.assertEqual(titles + 4, choices)
        # A port's name is found by shifting the port, in the patch and in the mod alike.
        self.assertEqual(name_bytes, 1 << 3)

    def test_the_patched_stock_code_reads_the_same_bytes(self):
        patches = STOCK_PATCHES.read_text(encoding="utf-8")
        loads = re.findall(r"(lbu?)\s+\$\w+, (\w+)\(\$at\)\s*$", patches, re.M)
        names, titles = address("gTrainerNames") - 0x80000000, address("gTrainerTitles") - 0x80000000
        self.assertEqual(sorted((op, int(offset, 16)) for op, offset in loads),
                         [("lb", names), ("lbu", titles), ("lbu", titles)])
        # A title is kept as its number XOR the player's own, and turned back the same way.
        turned_back = re.findall(r"xori\s+\$a1, \$a1, (\w+)\s*$", patches, re.M)
        self.assertEqual([int(value, 16) for value in turned_back], [constant("PLAYER_TRAINER_TITLE")] * 2)


@unittest.skipUnless(BASE_ROM.exists(), "no baserom; run tools/mod/check_rom.py")
class TrainerTitlesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = BASE_ROM.read_bytes()
        cls.bank = gen_trainer_titles.titles(cls.rom)
        cls.choices = gen_trainer_titles.choices(cls.rom)

    def test_the_generated_list_is_up_to_date(self):
        generated = (REPO_ROOT / "mod" / "data" / "trainer_titles.inc.c").read_text(encoding="ascii")
        self.assertEqual(generated, gen_trainer_titles.render(self.choices))

    def test_the_mod_and_the_generator_agree_on_the_bank(self):
        self.assertEqual(constant("TRAINER_TITLES_ROM"), gen_trainer_titles.TITLES_ROM)
        self.assertEqual(constant("PLAYER_TRAINER_TITLE"), gen_trainer_titles.PLAYER_TITLE)
        self.assertEqual(self.bank[gen_trainer_titles.PLAYER_TITLE], b"POK\xe9MON TRAINER")

    def test_the_list_is_every_different_title_once_with_the_players_own_first(self):
        self.assertEqual(self.choices[0], gen_trainer_titles.PLAYER_TITLE)
        chosen = [self.bank[number] for number in self.choices]
        self.assertEqual(len(set(chosen)), len(chosen))
        self.assertEqual(set(chosen), {title for title in self.bank if title.strip()})
        # A number is kept in a byte, XOR the player's own.
        self.assertLess(max(self.choices), 0x100)

    def test_a_title_fits_what_the_window_reads_for_it(self):
        # The read starts on an even address, so a title can begin a byte into it.
        size = int(re.search(r"^#define TRAINER_TITLE_BYTES (\w+)", TRAINER_H.read_text(encoding="utf-8"), re.M).group(1), 0)
        self.assertLess(1 + max(len(self.bank[number]) for number in self.choices), size)


if __name__ == "__main__":
    unittest.main()
