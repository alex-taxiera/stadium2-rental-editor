"""The editor on a console with 4 MB of RAM, using the test ROM from tools/mod/make_4mb_rom.py.

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import unittest

import harness as h
from harness import DOWN, RIGHT, UP, press, presses

# What the stock picker leaves free in the main pool on 4 MB. The mod's fragment comes
# out of this, with the 16 bytes the pool puts in front of every block.
STOCK_PICKER_FREE = 0x2C780
BLOCK_HEADER = 0x10
# Keeps the lowest the pool's free count has been, checked every frame.
WATCH = ('eval pool_low = 0x7FFFFFFF; event.onframeend(function() '
         f'local free = memory.read_u32_be(0x{h.POOL_FREE - 0x80000000:X}, "RDRAM"); '
         'if free < pool_low then pool_low = free end end, "pool_low")')
UNWATCH = 'eval event.unregisterbyname("pool_low"); return pool_low'


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class WithoutExpansionPakTest(h.EmulatorTest):
    rom = h.ROM_4MB

    def test_editor_needs_no_more_memory_than_the_mod_itself(self):
        self.start()
        self.assertEqual(self.s.u32(h.RAM_SIZE), 0x400000)
        free = self.s.u32(h.POOL_FREE)
        self.assertEqual(free, STOCK_PICKER_FREE - self.s.mod_size - BLOCK_HEADER)

        # Open a rental and use every part of the editor: a DV change that reloads the
        # model, the move list, and the keyboard.
        self.do(WATCH, *h.OPEN_EDITOR,
                *press(RIGHT), *press("A"), *press(UP), *press("A"),
                *presses(DOWN, 3), *press("A"), *press(UP), *press("A"), "wait 30",
                *press(h.LEFT), *presses(UP, 4), *press("A", 20), *press(DOWN), *press("B", 20),
                *press(UP), *press("A", 20), *press("A"), *press("Start"), *press("A", 40))
        record = self.s.record()
        self.assertEqual(record.dvs, 0xAAAA)
        self.assertEqual(record.nickname, b"ABRAA")
        self.assertStatsFollow(record)
        # Then out of the editor and the Pokemon entered; the editor again on it where it
        # now is, with another change that reloads the model.
        self.do(*press("B", 30), *press("A", 90), *press("Start", 60), *h.EDIT_POKEMON, *h.OPEN_MEMBER,
                *press(RIGHT), *press("A"), *press("L"), *press("A"), "wait 30", *presses("B", 2, 40))
        self.assertEqual(self.s.party().dvs, 0x0AAA)
        self.assertStatsFollow(self.s.party())
        # And a trainer picture and a title read from the ROM.
        self.do(*h.CHANGE_TRAINER, *presses(RIGHT, 3), *press(UP), *press(h.LEFT))
        self.assertEqual(self.s.trainer_state().title_text, b"RIVAL")
        self.do(*press("A", 40))
        self.assertEqual(self.s.trainer_choices(), [3, 0, 0, 0])
        self.assertEqual(int(float(self.s.run(UNWATCH)[0])), free)
        self.assertEqual(self.s.u32(h.POOL_FREE), free)


if __name__ == "__main__":
    unittest.main()
