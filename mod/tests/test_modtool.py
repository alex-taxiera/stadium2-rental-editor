"""Hook thunks and injection. Run: python3 -m unittest discover mod/tests"""

import shutil
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

    def test_call_thunk(self):
        words = modtool.call_thunk(2, FRAGMENT_LOAD, 0x16061C0, 0x1606A00, MAP_ENTRY)
        self.assertEqual(len(words), 32)
        self.assertEqual(words[0], 0x27BDFFD0)    # addiu sp, sp, -0x30
        self.assertEqual(words[1], 0xAFBF002C)    # sw    ra, 0x2C(sp)
        self.assertEqual(words[2:6], [0xAFA40030, 0xAFA50034, 0xAFA60038, 0xAFA7003C])
        # The fragment map's entry for the mod, base and size, kept on the stack.
        self.assertEqual(words[6:9], [0x3C08800D, 0x8D09C830, 0x8D08C834])   # lui t0 / lw t1 / lw t0
        self.assertEqual(words[9:11], [0xAFA90020, 0xAFA80024])
        self.assertEqual(words[11], 0x24040040)   # addiu a0, zero, 0x40
        self.assertEqual(words[12:14], [0x3C050160, 0x24A561C0])
        self.assertEqual((words[14], words[16]), (0x3C060160, 0x24C66A00))
        self.assertEqual(words[15], 0x0C0011FE)   # jal   Fragment_Load
        self.assertEqual(words[17:21], [0x8FA40030, 0x8FA50034, 0x8FA60038, 0x8FA7003C])
        self.assertEqual(words[21], 0x24590030)   # addiu t9, v0, 0x30: the third slot
        self.assertEqual(words[22:24], [0x0320F809, 0])   # jalr t9
        # And put back, whatever the call left there.
        self.assertEqual(words[24:26], [0x8FA90020, 0x8FB90024])
        self.assertEqual(words[26:29], [0x3C08800D, 0xAD09C830, 0xAD19C834])
        self.assertEqual(words[29:], [0x8FBF002C, 0x03E00008, 0x27BD0030])   # lw ra / jr ra / addiu sp


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

    def test_a_boot_hook_is_required(self):
        with self.assertRaises(ValueError):
            modtool.read_hooks(self.write("jump func_B Mod_B\n"))
        with self.assertRaises(ValueError):
            modtool.read_hooks(self.write("call func_B Mod_B\n"))
        # One for each screen the mod stays loaded on.
        self.assertEqual(len(modtool.read_hooks(self.write("boot a b\nboot c d\n"))), 2)

    def test_malformed_line_is_rejected(self):
        with self.assertRaises(ValueError):
            modtool.read_hooks(self.write("boot func_A\n"))
        with self.assertRaises(ValueError):
            modtool.read_hooks(self.write("boot a b\nreplace func_B Mod_B\n"))

    def test_a_detour_is_a_hook_like_any_other(self):
        hooks = modtool.read_hooks(self.write("boot a b\ndetour func_C orig_func_C\ncall func_D Mod_D\n"))
        self.assertEqual([(hook["kind"], hook["slot"]) for hook in hooks[1:]], [("detour", 1), ("call", 2)])

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


class GeneratedAsmTest(unittest.TestCase):
    FUNCTION = """glabel func_80000400
    /* 000400 80000400 27BDFFE8 */  addiu       $sp, $sp, -0x18
    /* 000404 80000404 03E00008 */  jr          $ra
    /* 000408 80000408 27BD0018 */   addiu      $sp, $sp, 0x18
"""
    HOOKS = [{"kind": "boot", "function": "func_80000400", "target": "orig_func_80000400", "slot": 0}]

    def generate(self, stock_patches):
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory)
        functions = directory / "asm" / "nonmatchings"
        functions.mkdir(parents=True)
        for name in ("func_80000400", "func_80000500"):
            (functions / f"{name}.s").write_text(self.FUNCTION.replace("func_80000400", name))
        modtool.write_asm(self.HOOKS, directory / "asm", directory / "out", {}, stock_patches)
        return directory / "out"

    def test_a_stock_patch_is_assembled_apart_from_the_mod(self):
        out = self.generate({"func_80000500": [(0x80000408, "addiu $sp, $sp, 0x20")]})
        patched = (out / "patched.s").read_text()
        self.assertIn("glabel patched_func_80000500", patched)
        self.assertIn("/* 000408 80000408 27BD0018 */   addiu $sp, $sp, 0x20", patched)
        self.assertNotIn("func_80000500", (out / "moved.s").read_text())
        self.assertNotIn("func_80000500", (out / "entry.s").read_text())

    def test_no_stock_patches_still_writes_the_file(self):
        self.assertNotIn("glabel", (self.generate({}) / "patched.s").read_text())

    def test_a_hooked_function_cannot_be_patched_in_place(self):
        with self.assertRaises(ValueError):
            self.generate({"func_80000400": [(0x80000408, "nop")]})

    def test_a_function_with_no_assembly_has_its_lines_assembled_alone(self):
        # The decompilation has it in C, so there is nothing to put the lines into.
        out = self.generate({"func_80000600": [(0x80000608, "addiu $sp, $sp, 0x20"), (0x8000060C, "nop")]})
        patched = (out / "patched.s").read_text()
        self.assertIn("glabel patched_func_80000600_80000608\n    addiu $sp, $sp, 0x20", patched)
        self.assertIn("glabel patched_func_80000600_8000060C\n    nop", patched)
        self.assertNotIn("glabel patched_func_80000600\n", patched)


class SplitAddressTest(unittest.TestCase):
    """A thunk that leaves the rest of its function in place must not cut an address in two."""

    HI, LO, JAL = fr.R_MIPS_HI16 << 24, fr.R_MIPS_LO16 << 24, fr.R_MIPS_26 << 24
    TABLE = [JAL | 0x00, HI | 0x08, LO | 0x0C, LO | 0x24, HI | 0x10, LO | 0x14]

    def test_whole_addresses_inside_or_outside_are_fine(self):
        self.assertIsNone(modtool.split_address(self.TABLE, 0x10, 0x18))
        self.assertIsNone(modtool.split_address(self.TABLE, 0x00, 0x08))
        self.assertIsNone(modtool.split_address(self.TABLE, 0x00, 0x28))

    def test_an_address_with_a_half_on_each_side_is_found(self):
        self.assertEqual(modtool.split_address(self.TABLE, 0x00, 0x14), 0x08)   # its second LO16 is at 0x24
        self.assertEqual(modtool.split_address(self.TABLE, 0x14, 0x18), 0x14)   # its HI16 is at 0x10


MOD_ROM = REPO_ROOT / "build" / "pokestadiumgs-us-mod.z64"
PATCHED_OBJ = REPO_ROOT / "build" / "mod" / "patched.o"
ASM_DIR = REPO_ROOT / "asm" / "us"
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

    @classmethod
    def hooks(cls):
        """The hooks, each with the stock fragment it is in and that fragment's place in the ROM."""
        hooks = modtool.read_hooks(REPO_ROOT / "mod" / "hooks.txt")
        for hook in hooks:
            number, section = modtool.stock_fragment(cls.elf, cls.elf.symbol(hook["function"]))
            hook["fragment"] = number
            hook["rom"] = cls.elf.symbol(f"fragment{number}_ROM_START")
            hook["at"] = hook["rom"] + cls.elf.symbol(hook["function"]) - section.addr
        return hooks

    def stock_patch_offsets(self):
        """Where in the ROM each instruction of mod/stock_patches.txt is."""
        offsets = []
        for patches in modtool.read_patches(REPO_ROOT / "mod" / "stock_patches.txt").values():
            for address, _ in patches:
                offsets.append(modtool.stock_home(self.elf, self.stock, address)[0])
        return offsets

    def test_only_hooked_code_the_tables_and_the_checksum_changed(self):
        fragments = {hook["fragment"]: hook["rom"] for hook in self.hooks()}
        self.assertEqual(sorted(fragments), [6, 14, 82, 83])
        # Take back the instructions patched in place and the trainer pictures' directory
        # (test_trainer_pictures.py has what that may change); then everything outside the
        # header checksum, the fragments with hooks in them and the hole is untouched.
        rom = bytearray(self.rom)
        for at in self.stock_patch_offsets():
            self.assertFalse(modtool.HOLE_START <= at < modtool.HOLE_END)
            rom[at:at + 4] = self.stock[at:at + 4]
        faces = modtool.gen_trainer_faces
        for lo, hi in ((faces.SLACK_START, faces.SLACK_END), (faces.table_entry(), faces.table_entry() + 4)):
            self.assertNotEqual(rom[lo:hi], self.stock[lo:hi])
            rom[lo:hi] = self.stock[lo:hi]
        changed = sorted((start, self.elf.symbol(f"fragment{number + 1}_ROM_START"))
                         for number, start in fragments.items())
        changed += [(modtool.HOLE_START, modtool.HOLE_END), (len(rom), len(rom))]
        lo = 0x18
        self.assertEqual(rom[:0x10], self.stock[:0x10])
        for start, end in changed:
            self.assertEqual(rom[lo:start], self.stock[lo:start], f"unexpected change in {lo:#x}-{start:#x}")
            lo = end

    def test_every_stock_patch_changed_its_instruction(self):
        offsets = self.stock_patch_offsets()
        self.assertTrue(offsets)
        for at in offsets:
            self.assertNotEqual(self.rom[at:at + 4], self.stock[at:at + 4], f"{at:#x}")

    def test_stock_patches_are_of_nothing_the_game_relocates(self):
        hooked = {hook["fragment"] for hook in self.hooks()}
        for patches in modtool.read_patches(REPO_ROOT / "mod" / "stock_patches.txt").values():
            at, relocated = modtool.stock_home(self.elf, self.rom, patches[0][0])
            for address, _ in patches:
                self.assertNotIn(at + address - patches[0][0], relocated)
            if not relocated:
                continue   # the main segment, which has no table
            # A fragment that only has patches keeps its table as it was.
            number, _ = modtool.stock_fragment(self.elf, patches[0][0])
            start = self.elf.symbol(f"fragment{number}_ROM_START")
            header = fr.read_header(self.rom, start)
            self.assertEqual(header, fr.read_header(self.stock, start))
            if number not in hooked:
                self.assertEqual(fr.read_table(self.rom, header), fr.read_table(self.stock, header))

    @unittest.skipUnless(PATCHED_OBJ.exists() and ASM_DIR.exists(), "no patched.o or extracted assembly")
    def test_a_relocated_instruction_cannot_be_patched_in_place(self):
        patched = fr.Elf(PATCHED_OBJ)
        every = modtool.read_patches(REPO_ROOT / "mod" / "stock_patches.txt")
        name, patches = next(iter(every.items()))
        number, section = modtool.stock_fragment(self.elf, patches[0][0])
        start = self.elf.symbol(f"fragment{number}_ROM_START")
        table = fr.read_table(self.stock, fr.read_header(self.stock, start))
        first, size = modtool.function_extent(modtool.find_function_asm(ASM_DIR, name))
        relocated = next(section.addr + (entry & fr.OFFSET_MASK) for entry in table
                         if first <= section.addr + (entry & fr.OFFSET_MASK) < first + size)
        rom = bytearray(self.stock)
        with self.assertRaises(ValueError):
            modtool.apply_stock_patches(rom, self.elf, patched, {name: [(relocated, "nop")]}, ASM_DIR)
        self.assertEqual(rom, self.stock)
        # The real ones go through, and give what the build gave.
        hooks = modtool.read_hooks(REPO_ROOT / "mod" / "hooks.txt")
        self.assertEqual(modtool.apply_stock_patches(rom, self.elf, patched, every, ASM_DIR, hooks),
                         sum(len(patches) for patches in every.values()))
        for at in self.stock_patch_offsets():
            self.assertEqual(rom[at:at + 4], self.rom[at:at + 4])

    @unittest.skipUnless(PATCHED_OBJ.exists() and ASM_DIR.exists(), "no patched.o or extracted assembly")
    def test_a_patch_under_a_thunk_is_refused(self):
        patched = fr.Elf(PATCHED_OBJ)
        hooks = modtool.read_hooks(REPO_ROOT / "mod" / "hooks.txt")
        every = modtool.read_patches(REPO_ROOT / "mod" / "stock_patches.txt")
        kept = next(hook for hook in hooks if hook["kind"] in modtool.KEEPS_BODY and hook["function"] in every)
        under = self.elf.symbol(kept["function"]) + 4
        with self.assertRaises(ValueError):
            modtool.apply_stock_patches(bytearray(self.stock), self.elf, patched,
                                        {kept["function"]: [(under, "nop")]}, ASM_DIR, hooks)

    def test_stock_fragment_tables_still_pass_the_order_check(self):
        for number, start in {hook["fragment"]: hook["rom"] for hook in self.hooks()}.items():
            header = fr.read_header(self.rom, start)
            stock_header = fr.read_header(self.stock, start)
            self.assertEqual(header, stock_header, number)   # size and layout untouched
            image = self.rom[start:start + header.reloc_offset]
            table = fr.read_table(self.rom, header)
            self.assertLess(len(table), len(fr.read_table(self.stock, stock_header)), number)
            self.assertEqual(fr.order_errors(image, table), [], number)

    def test_hooked_functions_start_with_thunks(self):
        first_words = {"boot": 0x27BDFFD8, "call": 0x27BDFFD0}   # addiu sp, sp, -0x28 and -0x30
        for hook in self.hooks():
            (first,) = struct.unpack_from(">I", self.rom, hook["at"])
            self.assertEqual(first, first_words.get(hook["kind"], 0x3C19800D), hook["function"])

    def test_the_mod_stays_loaded_only_where_it_is_booted(self):
        hooks = self.hooks()
        homes = {hook["fragment"] for hook in hooks if hook["kind"] == "boot"}
        self.assertEqual(homes, {14, 82})
        for hook in hooks:
            self.assertEqual(hook["fragment"] in homes, hook["kind"] != "call", hook["function"])

    @unittest.skipUnless(ASM_DIR.exists(), "no extracted assembly")
    def test_only_a_detour_or_a_call_keeps_the_rest_of_its_function(self):
        hooks = self.hooks()
        self.assertEqual({hook["kind"] for hook in hooks}, set(modtool.HOOK_KINDS))
        patched = set(self.stock_patch_offsets())
        for hook in hooks:
            _, size = modtool.function_extent(modtool.find_function_asm(ASM_DIR, hook["function"]))
            thunk = 4 * len(modtool.thunk(hook, 0, 0, 0, 0))
            rest = range(hook["at"] + thunk, hook["at"] + size, 4)
            if hook["kind"] in modtool.KEEPS_BODY:
                for at in rest:
                    if at not in patched:
                        self.assertEqual(self.rom[at:at + 4], self.stock[at:at + 4], hook["function"])
            else:
                self.assertEqual(self.rom[rest.start:rest.stop].count(0), size - thunk, hook["function"])


@unittest.skipUnless(ASM_DIR.exists(), "no extracted assembly")
class DecompilationTest(unittest.TestCase):
    """A hook needs its function's assembly, which the decompilation stops writing when
    it has the function in C; an old file can linger and hide that until the next fresh
    extract. So the sources are asked."""

    def test_hooked_functions_are_still_assembly_in_the_decompilation(self):
        sources = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                             for path in (REPO_ROOT / "src").rglob("*.c"))
        for hook in modtool.read_hooks(REPO_ROOT / "mod" / "hooks.txt"):
            name = hook["function"]
            self.assertRegex(sources, rf'GLOBAL_ASM\("[^"]*/{name}(_manual)?\.s"\)', name)


if __name__ == "__main__":
    unittest.main()
