"""Hook thunks and injection. Run: python3 -m unittest discover mod/tests"""

import struct
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import fragment_relocs as fr  # noqa: E402
import modtool  # noqa: E402

MAP_ENTRY = 0x800CC630 + 0x40 * 8
FRAGMENT_LOAD = 0x800047F8


class ThunkTest(unittest.TestCase):
    def test_slot_offsets_follow_the_header(self):
        self.assertEqual(modtool.slot_offset(0), 0x20)
        self.assertEqual(modtool.slot_offset(3), 0x38)

    def test_jump_thunk(self):
        self.assertEqual(modtool.jump_thunk(1, MAP_ENTRY), [
            0x3C19800D,  # lui   t9, 0x800D          (0x800CC830 rounds up)
            0x8F39C830,  # lw    t9, -0x37D0(t9)
            0x27390028,  # addiu t9, t9, 0x28
            0x03200008,  # jr    t9
            0x00000000,  # nop
        ])

    def test_boot_thunk(self):
        words = modtool.boot_thunk(0, FRAGMENT_LOAD, 0x16061C0, 0x1606A00)
        self.assertEqual(len(words), 20)
        self.assertEqual(words[0], 0x27BDFFD8)    # addiu sp, sp, -0x28
        self.assertEqual(words[1], 0xAFBF0024)    # sw    ra, 0x24(sp)
        self.assertEqual(words[2:6], [0xAFA40028, 0xAFA5002C, 0xAFA60030, 0xAFA70034])
        self.assertEqual(words[6], 0x24040040)    # addiu a0, zero, 0x40
        self.assertEqual(words[7:9], [0x3C050160, 0x24A561C0])   # a1 = 0x16061C0
        self.assertEqual(words[9], 0x3C060160)    # lui   a2, 0x160
        self.assertEqual(words[10], 0x0C0011FE)   # jal   Fragment_Load
        self.assertEqual(words[11], 0x24C66A00)   # addiu a2, a2, 0x6A00   (delay slot)
        self.assertEqual(words[12], 0x8FBF0024)   # lw    ra, 0x24(sp)
        self.assertEqual(words[13:17], [0x8FA40028, 0x8FA5002C, 0x8FA60030, 0x8FA70034])
        self.assertEqual(words[17], 0x24590020)   # addiu t9, v0, 0x20
        self.assertEqual(words[18:], [0x03200008, 0x27BD0028])   # jr t9 / addiu sp, sp, 0x28

    def test_boot_thunk_rounds_the_upper_half_for_a_negative_lower_half(self):
        words = modtool.boot_thunk(0, FRAGMENT_LOAD, 0x1608000, 0x160FFF0)
        self.assertEqual(words[7:9], [0x3C050161, 0x24A58000])
        self.assertEqual((words[9], words[11]), (0x3C060161, 0x24C6FFF0))


class HooksFileTest(unittest.TestCase):
    def write(self, text):
        handle = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_slots_follow_file_order(self):
        hooks = modtool.read_hooks(self.write(
            "# comment\nboot func_A orig_func_A\n\njump func_B Mod_B  # trailing\n"))
        self.assertEqual([(h["kind"], h["function"], h["target"], h["slot"]) for h in hooks],
                         [("boot", "func_A", "orig_func_A", 0), ("jump", "func_B", "Mod_B", 1)])

    def test_exactly_one_boot_hook(self):
        with self.assertRaises(ValueError):
            modtool.read_hooks(self.write("jump func_B Mod_B\n"))
        with self.assertRaises(ValueError):
            modtool.read_hooks(self.write("boot a b\nboot c d\n"))

    def test_malformed_line_is_rejected(self):
        with self.assertRaises(ValueError):
            modtool.read_hooks(self.write("boot func_A\n"))

    def test_the_real_hooks_file_parses(self):
        hooks = modtool.read_hooks(REPO_ROOT / "mod" / "hooks.txt")
        self.assertEqual(hooks[0]["kind"], "boot")


class FunctionExtentTest(unittest.TestCase):
    def test_counts_only_code(self):
        source = """\
.section .late_rodata
dlabel jtbl_80001000
    /* 001000 80001000 80000410 */ .word .L80000410

.section .text
glabel func_80000400
    /* 000400 80000400 27BDFFE8 */  addiu       $sp, $sp, -0x18
    /* 000404 80000404 03E00008 */  jr          $ra
  .L80000408:
    /* 000408 80000408 27BD0018 */   addiu      $sp, $sp, 0x18
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "func_80000400.s"
            path.write_text(source)
            self.assertEqual(modtool.function_extent(path), (0x80000400, 12))


class AsmPatchTest(unittest.TestCase):
    SOURCE = """glabel func_80000400
    /* 000400 80000400 27BDFFE8 */  addiu       $sp, $sp, -0x18
    /* 000404 80000404 0C000200 */  jal         func_80000800
    /* 000408 80000408 24A50070 */   addiu      $a1, $a1, 0x70
"""

    def test_replaces_the_instruction_at_an_address(self):
        patched = modtool.apply_patches("func_80000400", self.SOURCE, [(0x80000408, "addiu $a1, $a1, 0x78")])
        self.assertIn("/* 000408 80000408 24A50070 */   addiu $a1, $a1, 0x78", patched)
        self.assertIn("jal         func_80000800", patched)

    def test_unknown_address_is_an_error(self):
        with self.assertRaises(ValueError):
            modtool.apply_patches("func_80000400", self.SOURCE, [(0x80000410, "nop")])

    def test_patch_file_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asm_patches.txt"
            path.write_text("# comment\nfunc_A 80000408 addiu $a1, $a1, 0x78  # why\n\nfunc_A 8000040C nop\n")
            self.assertEqual(modtool.read_patches(path),
                             {"func_A": [(0x80000408, "addiu $a1, $a1, 0x78"), (0x8000040C, "nop")]})
            self.assertEqual(modtool.read_patches(Path(directory) / "missing.txt"), {})

    def test_the_real_patch_file_only_touches_hooked_functions(self):
        hooked = {h["function"] for h in modtool.read_hooks(REPO_ROOT / "mod" / "hooks.txt")}
        patches = modtool.read_patches(REPO_ROOT / "mod" / "asm_patches.txt")
        self.assertTrue(patches)
        self.assertLessEqual(set(patches), hooked)


MOD_ROM = REPO_ROOT / "build" / "pokestadiumgs-us-mod.z64"
STOCK_ROM = REPO_ROOT / "build" / "pokestadiumgs-us.z64"
GAME_ELF = REPO_ROOT / "build" / "pokestadiumgs-us.elf"


@unittest.skipUnless(MOD_ROM.exists() and STOCK_ROM.exists() and GAME_ELF.exists(),
                     "no modded ROM; run tools/mod/wsl_build.sh mod")
class InjectedRomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom, cls.stock = MOD_ROM.read_bytes(), STOCK_ROM.read_bytes()
        cls.elf = fr.Elf(GAME_ELF)
        cls.header = fr.read_header(cls.rom, modtool.HOLE_START)

    def test_fragment_sits_in_the_hole(self):
        self.assertEqual(self.header.header_size, fr.HEADER_SIZE)
        self.assertLessEqual(modtool.HOLE_START + self.header.size_in_rom, modtool.HOLE_END)
        self.assertEqual(fr.jump_target(self.header.inst, modtool.MOD_VRAM),
                         modtool.MOD_VRAM + modtool.slot_offset(0))
        after = self.rom[modtool.HOLE_START + self.header.size_in_rom:modtool.HOLE_END]
        self.assertEqual(after.count(0xFF), len(after))

    def test_fragment_table_is_loadable(self):
        image = self.rom[modtool.HOLE_START:modtool.HOLE_START + self.header.reloc_offset]
        table = fr.read_table(self.rom, self.header)
        self.assertEqual(table[0], fr.R_MIPS_26 << 24)   # the header's own jump
        self.assertEqual(fr.order_errors(image, table), [])

    def test_only_hooked_code_the_table_and_the_checksum_changed(self):
        start = self.elf.symbol(f"fragment{modtool.STOCK_FRAGMENT}_ROM_START")
        end = self.elf.symbol(f"fragment{modtool.STOCK_FRAGMENT + 1}_ROM_START")
        # Everything outside the header checksum, fragment 14 and the hole is untouched.
        for lo, hi in ((0, 0x10), (0x18, start), (end, modtool.HOLE_START), (modtool.HOLE_END, len(self.rom))):
            self.assertEqual(self.rom[lo:hi], self.stock[lo:hi], f"unexpected change in {lo:#x}-{hi:#x}")

    def test_stock_fragment_table_still_passes_the_order_check(self):
        start = self.elf.symbol(f"fragment{modtool.STOCK_FRAGMENT}_ROM_START")
        header = fr.read_header(self.rom, start)
        stock_header = fr.read_header(self.stock, start)
        self.assertEqual(header, stock_header)   # size and layout untouched
        image = self.rom[start:start + header.reloc_offset]
        table = fr.read_table(self.rom, header)
        self.assertLess(len(table), len(fr.read_table(self.stock, stock_header)))
        self.assertEqual(fr.order_errors(image, table), [])

    def test_hooked_functions_start_with_thunks(self):
        start = self.elf.symbol(f"fragment{modtool.STOCK_FRAGMENT}_ROM_START")
        vram = self.elf.by_name[f".fragment{modtool.STOCK_FRAGMENT}"].addr
        for hook in modtool.read_hooks(REPO_ROOT / "mod" / "hooks.txt"):
            at = start + self.elf.symbol(hook["function"]) - vram
            (first,) = struct.unpack_from(">I", self.rom, at)
            expected = 0x27BDFFD8 if hook["kind"] == "boot" else 0x3C19800D
            self.assertEqual(first, expected, hook["function"])


if __name__ == "__main__":
    unittest.main()
