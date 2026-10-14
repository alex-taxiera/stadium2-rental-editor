"""Relocation table generation. Run: python3 -m unittest discover mod/tests"""

import struct
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import fragment_relocs as fr  # noqa: E402

VRAM = 0x85000000
T0, T1, A1 = 8, 9, 5


def lui(register, imm):
    return 0x3C000000 | (register << 16) | imm


def addiu(rt, rs, imm):
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def jal(target):
    return 0x0C000000 | ((target & 0x0FFFFFFF) >> 2)


def image_of(words):
    return struct.pack(f">{len(words)}I", *words)


def hi_lo(address):
    low = address & 0xFFFF
    return ((address >> 16) + (1 if low & 0x8000 else 0)) & 0xFFFF, low


class Program:
    """A tiny fragment: instruction words plus the relocations a linker would keep."""

    def __init__(self):
        self.words, self.relocs = [], []

    def emit(self, word, kind=None, target=0):
        if kind is not None:
            self.relocs.append(fr.Reloc(VRAM + len(self.words) * 4, kind, target, len(self.relocs)))
        self.words.append(word)
        return (len(self.words) - 1) * 4

    def load_address(self, register, address):
        high, low = hi_lo(address)
        a = self.emit(lui(register, high), fr.R_MIPS_HI16, address)
        b = self.emit(addiu(register, register, low), fr.R_MIPS_LO16, address)
        return a, b

    def table(self):
        return fr.build_entries(self.relocs, VRAM, image_of(self.words))


class HeaderTest(unittest.TestCase):
    def test_entry_jump_round_trips(self):
        self.assertEqual(fr.entry_jump(0x813029F0), 0x084C0A7C)  # fragment 14's real header
        self.assertEqual(fr.jump_target(0x084C0A7C, 0x81300000), 0x813029F0)

    def test_fragment_ids(self):
        self.assertEqual(fr.fragment_id(0x81300000), 0x03)
        self.assertEqual(fr.fragment_vram(0x40), 0x85000000)

    def test_header_layout(self):
        header = fr.pack_header(0x85000020, 0x400, 0x500, 0x480)
        self.assertEqual(len(header), fr.HEADER_SIZE)
        parsed = fr.read_header(header, 0)
        self.assertEqual((parsed.inst, parsed.header_size, parsed.reloc_offset,
                          parsed.size_in_rom, parsed.size_in_ram),
                         (fr.entry_jump(0x85000020), 0x20, 0x400, 0x500, 0x480))

    def test_table_round_trips(self):
        entries = [0x05000020, 0x06000024, 0x84000028]
        packed = fr.pack_table(entries)
        header = fr.Header(0, 0, 0x20, 0, len(packed), len(packed))
        self.assertEqual(fr.read_table(packed, header), entries)


class BuildEntriesTest(unittest.TestCase):
    def test_internal_and_external_targets(self):
        p = Program()
        p.emit(jal(VRAM + 0x100), fr.R_MIPS_26, VRAM + 0x100)
        p.emit(jal(0x80002B24), fr.R_MIPS_26, 0x80002B24)
        p.emit(jal(0x81600A34), fr.R_MIPS_26, 0x81600A34)
        entries, unpaired = p.table()
        self.assertEqual(unpaired, [])
        self.assertEqual(entries, [0x04000000, 0x84000004, 0x84000008])

    def test_low_half_follows_its_high_half(self):
        p = Program()
        hi, _ = p.load_address(T0, VRAM + 0x1234)
        entries, _ = p.table()
        self.assertEqual(entries, [0x05000000 | hi, 0x06000004])
        self.assertEqual(fr.order_errors(image_of(p.words), entries), [])

    def test_low_half_is_pulled_up_behind_its_high_half(self):
        # lui; jal; addiu (delay slot): the LO16 entry must precede the jal entry.
        p = Program()
        high, low = hi_lo(VRAM + 0x2000)
        p.emit(lui(T0, high), fr.R_MIPS_HI16, VRAM + 0x2000)
        p.emit(jal(0x80001000), fr.R_MIPS_26, 0x80001000)
        p.emit(addiu(T0, T0, low), fr.R_MIPS_LO16, VRAM + 0x2000)
        entries, _ = p.table()
        self.assertEqual([fr.describe(e) for e in entries], ["HI16@0x0", "LO16@0x8", "26x@0x4"])

    def test_every_high_half_gets_a_low_half(self):
        # Two `lui` back to back on one register (one hoisted into a delay slot), each
        # with its own low half further on. Nearest-before alone starves the first.
        p = Program()
        first, second = VRAM + 0x71C, VRAM + 0x750
        p.emit(lui(A1, hi_lo(second)[0]), fr.R_MIPS_HI16, second)
        p.emit(lui(A1, hi_lo(first)[0]), fr.R_MIPS_HI16, first)
        p.emit(addiu(A1, A1, hi_lo(first)[1]), fr.R_MIPS_LO16, first)
        p.emit(0)
        p.emit(addiu(A1, A1, hi_lo(second)[1]), fr.R_MIPS_LO16, second)
        entries, _ = p.table()
        self.assertEqual([fr.describe(e) for e in entries],
                         ["HI16@0x0", "LO16@0x10", "HI16@0x4", "LO16@0x8"])
        self.assertEqual(fr.order_errors(image_of(p.words), entries), [])

    def test_a_low_half_that_counts_down_keeps_its_own_high_half(self):
        # As the linker leaves them, relocations against the fragment's own data all name
        # the start of its section. An address past the first 0x8000 bytes has a negative
        # lower half, which measured from that start looks nearer to the `lui` of a lower
        # address than to its own. Here it would go to the one that follows, and from
        # there to the first, which has none of its own and is given one.
        p = Program()
        low_data, high_data = VRAM + 0x7EC0, VRAM + 0xA17C
        p.emit(lui(A1, hi_lo(low_data + 4)[0]), fr.R_MIPS_HI16, VRAM)
        p.emit(lui(A1, hi_lo(low_data)[0]), fr.R_MIPS_HI16, VRAM)
        p.emit(addiu(A1, A1, hi_lo(low_data)[1]), fr.R_MIPS_LO16, VRAM)
        p.emit(addiu(A1, A1, hi_lo(low_data + 4)[1]), fr.R_MIPS_LO16, VRAM)
        own = p.emit(lui(A1, hi_lo(high_data)[0]), fr.R_MIPS_HI16, VRAM)
        down = p.emit(addiu(A1, A1, hi_lo(high_data)[1]), fr.R_MIPS_LO16, VRAM)
        p.emit(lui(A1, hi_lo(low_data)[0]), fr.R_MIPS_HI16, VRAM)
        p.emit(addiu(A1, A1, hi_lo(low_data)[1]), fr.R_MIPS_LO16, VRAM)
        entries, unpaired = p.table()
        self.assertEqual(unpaired, [])
        at = entries.index(0x05000000 | own)
        self.assertEqual(entries[at + 1], 0x06000000 | down)
        self.assertEqual(fr.order_errors(image_of(p.words), entries), [])

    def test_high_half_placed_after_its_low_half(self):
        # The `lui` for the first use sits later in the file; an unrelated one precedes.
        p = Program()
        p.load_address(T0, 0x800A1234)
        late = VRAM + 0x40000
        low_at = p.emit(addiu(T0, T0, hi_lo(late)[1]), fr.R_MIPS_LO16, late)
        high_at = p.emit(lui(T0, hi_lo(late)[0]), fr.R_MIPS_HI16, late)
        entries, _ = p.table()
        self.assertEqual(entries[-2:], [0x05000000 | high_at, 0x06000000 | low_at])
        self.assertEqual(fr.order_errors(image_of(p.words), entries), [])

    def test_low_half_without_high_half_is_reported(self):
        p = Program()
        at = p.emit(addiu(T1, T1, 0x10), fr.R_MIPS_LO16, VRAM + 0x10)
        entries, unpaired = p.table()
        self.assertEqual((entries, unpaired), ([], [at]))

    def test_range_limits_what_is_listed(self):
        p = Program()
        p.emit(jal(VRAM + 0x100), fr.R_MIPS_26, VRAM + 0x100)
        p.emit(jal(VRAM + 0x200), fr.R_MIPS_26, VRAM + 0x200)
        entries, _ = fr.build_entries(p.relocs, VRAM, image_of(p.words), 4, 8)
        self.assertEqual(entries, [0x04000004])


class RelocateTest(unittest.TestCase):
    def test_matches_a_direct_relink(self):
        """Relocating to a new base must equal building the same code at that base."""
        def build(base):
            p = Program()
            p.load_address(T0, base + 0x87F0)          # low half is negative
            p.emit(jal(base + 0x40), fr.R_MIPS_26, base + 0x40)
            p.load_address(T1, 0x800A5678)             # main segment: must not move
            p.emit(base + 0x123C, fr.R_MIPS_32, base + 0x123C)
            return p

        original = build(VRAM)
        entries, _ = original.table()
        new_base = 0x8024B7A8
        moved = fr.relocate(image_of(original.words), entries, {fr.fragment_id(VRAM): new_base})
        self.assertEqual(moved, image_of(build(new_base).words))

    def test_unloaded_fragment_references_are_left_alone(self):
        p = Program()
        p.emit(jal(0x81600A34), fr.R_MIPS_26, 0x81600A34)
        entries, _ = p.table()
        image = image_of(p.words)
        self.assertEqual(fr.relocate(image, entries, {}), image)
        moved = fr.relocate(image, entries, {fr.fragment_id(0x81600000): 0x80148A90})
        self.assertEqual(struct.unpack(">I", moved)[0], jal(0x80148A90 + 0xA34))

    def test_order_check_catches_a_starved_high_half(self):
        p = Program()
        hi, lo = p.load_address(T0, VRAM + 0x100)
        image = image_of(p.words)
        self.assertEqual(fr.order_errors(image, [0x06000000 | lo, 0x05000000 | hi]), [hi])


class SharedHighHalfTest(unittest.TestCase):
    def test_one_lui_serving_two_addresses_is_reported(self):
        p = Program()
        high, low = hi_lo(VRAM + 0x400)
        at = p.emit(lui(T0, high), fr.R_MIPS_HI16, VRAM + 0x400)
        p.emit(addiu(T1, T0, low), fr.R_MIPS_LO16, VRAM + 0x400)
        p.emit(addiu(T1, T0, low + 4), fr.R_MIPS_LO16, VRAM + 0x404)
        entries, _ = p.table()
        self.assertEqual(fr.shared_high_halves(image_of(p.words), entries),
                         {at: [VRAM + 0x400, VRAM + 0x404]})

    def test_repeated_use_of_one_address_is_fine(self):
        p = Program()
        high, low = hi_lo(VRAM + 0x400)
        p.emit(lui(T0, high), fr.R_MIPS_HI16, VRAM + 0x400)
        p.emit(addiu(T1, T0, low), fr.R_MIPS_LO16, VRAM + 0x400)
        p.emit(addiu(T1, T0, low), fr.R_MIPS_LO16, VRAM + 0x400)
        entries, _ = p.table()
        self.assertEqual(fr.shared_high_halves(image_of(p.words), entries), {})


class MergeTest(unittest.TestCase):
    def test_replaces_only_the_given_range(self):
        stock = [0x04000020, 0x05000040, 0x06000044, 0x04000060, 0x02000100]
        merged = fr.merge_table(stock, [0x84000040], [(0x40, 0x60)])
        self.assertEqual(merged, [0x04000020, 0x84000040, 0x04000060, 0x02000100])

    def test_appends_when_nothing_was_there(self):
        self.assertEqual(fr.merge_table([0x04000020], [0x04000080], [(0x80, 0x90)]),
                         [0x04000020, 0x04000080])

    def test_can_only_remove(self):
        self.assertEqual(fr.merge_table([0x04000020, 0x04000040], [], [(0x40, 0x44)]), [0x04000020])


ELF = REPO_ROOT / "build" / "pokestadiumgs-us.elf"
ROM = REPO_ROOT / "build" / "pokestadiumgs-us.z64"


@unittest.skipUnless(ELF.exists() and ROM.exists(), "no built ROM; run tools/mod/wsl_build.sh")
class StockFragmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf, cls.rom = fr.Elf(ELF), ROM.read_bytes()

    def test_finds_all_88_fragments(self):
        self.assertEqual(len(fr.find_fragments(self.rom)), 88)

    def test_fragment_14_is_reproduced_exactly(self):
        result = fr.compare_text(self.elf, self.rom, 14)
        self.assertEqual(result["id"], 0x03)
        self.assertEqual((result["stock"], result["common"]), (1953, 1953))
        self.assertEqual(result["stock_only"], [])
        self.assertEqual(result["differing_words"], 0)
        self.assertEqual(result["built_order_errors"], 0)

    def test_stock_tables_pass_the_order_check(self):
        for number in (1, 14, 15, 24, 67, 79):
            header = fr.read_header(self.rom, self.elf.symbol(f"fragment{number}_ROM_START"))
            image = self.rom[header.rom_start:header.rom_start + header.reloc_offset]
            self.assertEqual(fr.order_errors(image, fr.read_table(self.rom, header)), [], number)


if __name__ == "__main__":
    unittest.main()
