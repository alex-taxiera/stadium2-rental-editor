#!/usr/bin/env python3
"""Fragment (overlay) headers and relocation tables for Pokemon Stadium 2.

A fragment is a relocatable module: a 0x20-byte header, code and data linked at a
virtual address of 0x81000000 + id * 0x100000, and a relocation table the loader
(Memmap_RelocateFragment) uses to rebase every reference into fragment space.

    header:  u32 inst[2]      jump to the entry point, and its delay slot
             char magic[8]    "FRAGMENT"
             u32 headerSize   0x20
             u32 relocOffset  offset of the table; BSS also starts here
             u32 sizeInRom
             u32 sizeInRam
    table:   u32 count, then count words of (flag << 31) | (type << 24) | offset

Every R_MIPS_32/26/HI16/LO16 relocation is listed, in the order the compiler emitted
them. That order matters: the loader pairs each LO16 with the most recent HI16 for
the same register, so entries must not be sorted by address. The flag marks a target
outside the fragment itself (main segment, another fragment, or an absolute value);
the loader ignores it and rebases any address that falls inside a loaded fragment.

Tables are built from the relocations the linker keeps with --emit-relocs. Stock
fragments have data pointers the disassembly leaves as plain numbers, so a stock
table is patched (see merge_table) rather than rebuilt.

    fragment_relocs.py verify <elf> <rom>    check the rebuilt text entries of every
                                             stock fragment against the ROM
    fragment_relocs.py show <rom> <number>   print one fragment's header

Standard library only.
"""

import argparse
import struct
import sys
from collections import namedtuple
from pathlib import Path

MAGIC = b"FRAGMENT"
HEADER_SIZE = 0x20
FRAGMENT_SPACE = range(0x81000000, 0x90000000)
FRAGMENT_SPAN = 0x100000

R_MIPS_32, R_MIPS_26, R_MIPS_HI16, R_MIPS_LO16 = 2, 4, 5, 6
TABLE_TYPES = (R_MIPS_32, R_MIPS_26, R_MIPS_HI16, R_MIPS_LO16)
EXTERNAL = 0x80000000
OFFSET_MASK = 0x00FFFFFF

SHT_SYMTAB, SHT_REL = 2, 9

Header = namedtuple("Header", "rom_start inst header_size reloc_offset size_in_rom size_in_ram")
Section = namedtuple("Section", "name type addr offset size link info")
Reloc = namedtuple("Reloc", "offset type target symbol")


def fragment_id(vram: int) -> int:
    return ((vram & 0x0FF00000) >> 20) - 0x10


def fragment_vram(frag_id: int) -> int:
    return 0x81000000 + frag_id * 0x100000


def entry_jump(entry: int) -> int:
    """The `j entry` instruction stored in a header."""
    return 0x08000000 | ((entry & 0x0FFFFFFF) >> 2)


def jump_target(inst: int, vram: int) -> int:
    return (vram & 0xF0000000) | ((inst & 0x03FFFFFF) << 2)


def pack_header(entry: int, reloc_offset: int, size_in_rom: int, size_in_ram: int) -> bytes:
    return struct.pack(">II8sIIII", entry_jump(entry), 0, MAGIC, HEADER_SIZE,
                       reloc_offset, size_in_rom, size_in_ram)


def pack_table(entries) -> bytes:
    return struct.pack(f">{len(entries) + 1}I", len(entries), *entries)


def read_header(rom: bytes, rom_start: int) -> Header:
    inst, _, magic, header_size, reloc_offset, size_in_rom, size_in_ram = struct.unpack_from(
        ">II8sIIII", rom, rom_start)
    if magic != MAGIC:
        raise ValueError(f"no fragment header at {rom_start:#x}")
    return Header(rom_start, inst, header_size, reloc_offset, size_in_rom, size_in_ram)


def read_table(rom: bytes, header: Header) -> list:
    base = header.rom_start + header.reloc_offset
    (count,) = struct.unpack_from(">I", rom, base)
    return list(struct.unpack_from(f">{count}I", rom, base + 4))


def find_fragments(rom: bytes, start: int = 0x1000, end: int = 0x440000) -> list:
    """Headers of every fragment stored uncompressed in the code area of the ROM."""
    headers = []
    pos = rom.find(MAGIC, start, end)
    while pos != -1:
        if pos % 8 == 0:
            headers.append(read_header(rom, pos - 8))
        pos = rom.find(MAGIC, pos + 8, end)
    return headers


class Elf:
    """Just enough of a big-endian ELF32 file to read sections, symbols and REL entries."""

    def __init__(self, path: Path):
        self.data = path.read_bytes()
        if self.data[:6] != b"\x7fELF\x01\x02":
            raise ValueError(f"{path} is not a big-endian ELF32 file")
        shoff, = struct.unpack_from(">I", self.data, 0x20)
        shentsize, shnum, shstrndx = struct.unpack_from(">HHH", self.data, 0x2E)
        raw = [struct.unpack_from(">IIIIIIIIII", self.data, shoff + i * shentsize) for i in range(shnum)]
        strtab = raw[shstrndx]
        self.sections = [
            Section(self._string(strtab[4], r[0]), r[1], r[3], r[4], r[5], r[6], r[7]) for r in raw
        ]
        self.by_name = {s.name: s for s in self.sections}
        self._symbols = None
        self._named = None

    def _string(self, table_offset: int, index: int) -> str:
        start = table_offset + index
        return self.data[start:self.data.index(b"\0", start)].decode("ascii", "replace")

    def contents(self, section: Section) -> bytes:
        return self.data[section.offset:section.offset + section.size]

    @property
    def symbol_values(self) -> list:
        if self._symbols is None:
            symtab = next(s for s in self.sections if s.type == SHT_SYMTAB)
            count = symtab.size // 16
            self._symbols = [struct.unpack_from(">I", self.data, symtab.offset + i * 16 + 4)[0]
                             for i in range(count)]
        return self._symbols

    def symbol(self, name: str) -> int:
        """Value of a named symbol, e.g. fragment14_ROM_START."""
        if self._named is None:
            symtab = next(s for s in self.sections if s.type == SHT_SYMTAB)
            strings = self.sections[symtab.link].offset
            self._named = {}
            for i in range(symtab.size // 16):
                name_index, value = struct.unpack_from(">II", self.data, symtab.offset + i * 16)
                if name_index:
                    start = strings + name_index
                    self._named[self.data[start:self.data.index(b"\0", start)]] = value
        return self._named[name.encode()]

    def relocations(self, section_name: str) -> list:
        """REL entries for a section as (address, type, symbol value), in file order."""
        rel = self.by_name.get(".rel" + section_name)
        if rel is None or rel.type != SHT_REL:
            return []
        values = self.symbol_values
        out = []
        for i in range(rel.size // 8):
            address, info = struct.unpack_from(">II", self.data, rel.offset + i * 8)
            out.append(Reloc(address, info & 0xFF, values[info >> 8], info >> 8))
        return out


def build_entries(relocations, vram: int, image: bytes, start: int = 0, end: int = FRAGMENT_SPAN):
    """Table entries for the relocations at fragment offsets [start, end).

    `image` is the fragment's linked contents, used to read the register each HI16/LO16
    instruction uses. Returns (entries, unpaired): entries in an order the loader handles
    correctly, and the offsets of LO16s it cannot pair (see below).

    The loader keeps one pending HI16 per register and applies each LO16 to the pending
    HI16 of its base register. So a LO16 must come after its own HI16 with no other HI16
    for that register in between. Each HI16 is therefore emitted with its LO16s directly
    behind it, which is also how the stock tables are laid out.

    What the loader needs from the pairing is less than the true one:
      * each LO16 is applied against a HI16 on its register holding the right upper half;
      * every HI16 has at least one LO16, or its `lui` is never rewritten.
    A LO16 goes to the nearest HI16 before it on the same register. When the nearest one
    after it would form an address closer to the relocation's symbol, that one is used
    instead: this is a `lui` hoisted into a later delay slot. A HI16 left with no LO16
    then takes one from the nearest HI16 with the same register and upper half that has
    one to spare. A LO16 with no HI16 on its register cannot be relocated by the loader
    and is reported.
    """
    wanted = sorted((r for r in relocations
                     if r.type in TABLE_TYPES and start <= r.offset - vram < end),
                    key=lambda r: r.offset)

    def word(reloc):
        return struct.unpack_from(">I", image, reloc.offset - vram)[0]

    def distance(high, low):
        imm = word(low) & 0xFFFF
        formed = ((word(high) & 0xFFFF) << 16) + (imm - 0x10000 if imm & 0x8000 else imm)
        return abs((formed & 0xFFFFFFFF) - low.target)

    by_register = {}  # register -> HI16 relocations, ascending
    groups = {}       # (register, upper half) -> HI16 relocations, ascending
    for r in wanted:
        if r.type == R_MIPS_HI16:
            register = (word(r) >> 16) & 0x1F
            by_register.setdefault(register, []).append(r)
            groups.setdefault((register, word(r) & 0xFFFF), []).append(r)

    followers = {}  # HI16 address -> its LO16 relocations
    unpaired = []
    for r in wanted:
        if r.type != R_MIPS_LO16:
            continue
        candidates = by_register.get((word(r) >> 21) & 0x1F, [])
        before = next((h for h in reversed(candidates) if h.offset < r.offset), None)
        after = next((h for h in candidates if h.offset > r.offset), None)
        if before is None and after is None:
            unpaired.append(r.offset - vram)
            continue
        if before is None or (after is not None and distance(after, r) < distance(before, r)):
            owner = after
        else:
            owner = before
        followers.setdefault(owner.offset, []).append(r)

    # Every HI16 needs a LO16. Give each empty one the best-fitting LO16 from a HI16 on
    # the same register that can spare it: first from those with the same upper half,
    # then from any. Taking a donor's only LO16 is allowed when it fits the new owner
    # strictly better, which then leaves the donor to be served on a later pass.
    for _ in range(4):
        empty = [h for group in by_register.values() for h in group if not followers.get(h.offset)]
        if not empty:
            break
        for high in empty:
            register = (word(high) >> 16) & 0x1F
            best = None
            for donor in by_register[register]:
                spare = followers.get(donor.offset, [])
                if donor is high or not spare:
                    continue
                same_half = (word(donor) & 0xFFFF) == (word(high) & 0xFFFF)
                for low in spare:
                    fits_better = distance(high, low) < distance(donor, low)
                    if len(spare) < 2 and not fits_better:
                        continue
                    # Among equal fits, leave the donor the LO16 right behind it.
                    key = (not same_half, distance(high, low), -abs(low.offset - donor.offset))
                    if best is None or key < best[0]:
                        best = (key, donor, low)
            if best:
                _, donor, low = best
                followers[donor.offset].remove(low)
                followers[high.offset] = [low]

    def entry(reloc):
        internal = vram <= reloc.target < vram + FRAGMENT_SPAN
        return (0 if internal else EXTERNAL) | (reloc.type << 24) | (reloc.offset - vram)

    entries = []
    for r in wanted:
        if r.type == R_MIPS_LO16:
            continue
        entries.append(entry(r))
        if r.type == R_MIPS_HI16:
            entries.extend(entry(lo) for lo in followers.get(r.offset, []))
    return entries, unpaired


def merge_table(stock: list, replacement: list, ranges) -> list:
    """Replace the stock entries that fall in `ranges` (fragment offsets) with new ones.

    Entries elsewhere keep their original order; the new entries go where the first
    replaced one was, or at the end if nothing was removed.
    """
    def replaced(entry):
        return any(lo <= (entry & OFFSET_MASK) < hi for lo, hi in ranges)

    merged, inserted = [], False
    for entry in stock:
        if not replaced(entry):
            merged.append(entry)
        elif not inserted:
            merged.extend(replacement)
            inserted = True
    return merged if inserted else merged + replacement


def relocate(image: bytes, table: list, fragment_map: dict) -> bytes:
    """Apply a table the way Memmap_RelocateFragment does.

    `fragment_map` maps fragment id -> load address for every loaded fragment,
    including the one being relocated.
    """
    rebase = rebase_with(fragment_map)
    out = bytearray(image)
    # The game's arrays are uninitialised; a LO16 with no HI16 before it reads garbage.
    # Model that as register 0 values so the result is deterministic and visibly wrong.
    lui_at = dict.fromkeys(range(32), 0)
    lui_value = dict.fromkeys(range(32), 0)
    for entry in table:
        offset = entry & OFFSET_MASK
        (word,) = struct.unpack_from(">I", out, offset)
        kind = (entry >> 24) & 0x7F
        if kind == R_MIPS_32:
            word = rebase(word)
        elif kind == R_MIPS_26:
            target = rebase(((word * 4) & 0x0FFFFFFC) + 0x80000000)
            word = ((target & 0x0FFFFFFF) >> 2) | (word & 0xFC000000)
        elif kind == R_MIPS_HI16:
            register = (word >> 16) & 0x1F
            lui_at[register], lui_value[register] = offset, word
            continue
        elif kind == R_MIPS_LO16:
            register = (word >> 21) & 0x1F
            low = word & 0xFFFF
            address = rebase((lui_value[register] << 16) + (low - 0x10000 if low & 0x8000 else low))
            (lui,) = struct.unpack_from(">I", out, lui_at[register])
            high = ((address >> 16) + (1 if address & 0x8000 else 0)) & 0xFFFF
            struct.pack_into(">I", out, lui_at[register], (lui & 0xFFFF0000) | high)
            word = (word & 0xFFFF0000) | (address & 0xFFFF)
        else:
            continue
        struct.pack_into(">I", out, offset, word)
    return bytes(out)


def rebase_with(fragment_map: dict):
    def rebase(address: int) -> int:
        address &= 0xFFFFFFFF
        if address in FRAGMENT_SPACE:
            base = fragment_map.get(fragment_id(address))
            if base:
                return (base + (address & 0xFFFFF)) & 0xFFFFFFFF
        return address
    return rebase


def expected_aligned(image: bytes, table: list, fragment_map: dict) -> bytes:
    """What relocation must produce when every fragment moves by a multiple of 0x10000.

    Such a move leaves every lower half untouched and shifts each `lui` by a fixed
    amount, so the answer does not depend on which LO16 belongs to which HI16. Comparing
    relocate() against this shows whether a table's order is one the loader handles.
    """
    rebase = rebase_with(fragment_map)
    out = bytearray(image)
    for entry in table:
        offset = entry & OFFSET_MASK
        (word,) = struct.unpack_from(">I", image, offset)
        kind = (entry >> 24) & 0x7F
        if kind == R_MIPS_32:
            word = rebase(word)
        elif kind == R_MIPS_26:
            target = rebase(((word * 4) & 0x0FFFFFFC) + 0x80000000)
            word = ((target & 0x0FFFFFFF) >> 2) | (word & 0xFC000000)
        elif kind == R_MIPS_HI16:
            word = (word & 0xFFFF0000) | (rebase((word & 0xFFFF) << 16) >> 16)
        struct.pack_into(">I", out, offset, word)
    return bytes(out)


def shared_high_halves(image: bytes, table: list) -> dict:
    """HI16s that the loader would apply to more than one address: offset -> addresses.

    After a move that is not a multiple of 0x10000, two such addresses can need
    different upper halves, and the loader can only write one.
    """
    pending, formed = {}, {}
    for entry in table:
        offset = entry & OFFSET_MASK
        (word,) = struct.unpack_from(">I", image, offset)
        kind = (entry >> 24) & 0x7F
        if kind == R_MIPS_HI16:
            pending[(word >> 16) & 0x1F] = (offset, word & 0xFFFF)
        elif kind == R_MIPS_LO16 and (word >> 21) & 0x1F in pending:
            at, high = pending[(word >> 21) & 0x1F]
            low = word & 0xFFFF
            address = ((high << 16) + (low - 0x10000 if low & 0x8000 else low)) & 0xFFFFFFFF
            formed.setdefault(at, set()).add(address)
    return {at: sorted(addresses) for at, addresses in formed.items() if len(addresses) > 1}


ALIGNED_MAP = {frag: 0x80400000 + frag * 0x30000 for frag in range(240)}


def order_errors(image: bytes, table: list) -> list:
    """Offsets the loader would get wrong for this table (empty when the order is sound)."""
    got = relocate(image, table, ALIGNED_MAP)
    want = expected_aligned(image, table, ALIGNED_MAP)
    return [i for i in range(0, len(image), 4) if got[i:i + 4] != want[i:i + 4]]


def describe(entry: int) -> str:
    names = {R_MIPS_32: "32", R_MIPS_26: "26", R_MIPS_HI16: "HI16", R_MIPS_LO16: "LO16"}
    kind = (entry >> 24) & 0x7F
    return f"{names.get(kind, hex(kind))}{'x' if entry & EXTERNAL else ''}@{entry & OFFSET_MASK:#x}"


def compare_text(elf: Elf, rom: bytes, number: int) -> dict:
    """How the entries rebuilt for one stock fragment's code compare with its ROM table."""
    name = f".fragment{number}"
    section = elf.by_name[name]
    header = read_header(rom, elf.symbol(f"fragment{number}_ROM_START"))
    text_end = elf.symbol(f"fragment{number}_TEXT_END") - section.addr
    stock = [e for e in read_table(rom, header) if HEADER_SIZE <= (e & OFFSET_MASK) < text_end]
    built, unpaired = build_entries(elf.relocations(name), section.addr, elf.contents(section),
                                    HEADER_SIZE, text_end)

    # Only an entry that changes what the loader does can break a fragment: one that is
    # internal, or that points into another fragment. Main-segment entries are no-ops.
    targets = {r.offset - section.addr: r.target for r in elf.relocations(name)}
    stock_set, built_set = set(stock), set(built)
    common_stock = [e for e in stock if e in built_set]
    common_built = [e for e in built if e in stock_set]

    # The real test: with every fragment loaded somewhere else, does the patched table
    # leave the code exactly as the stock table does?
    full_stock = read_table(rom, header)
    patched = merge_table(full_stock, built, [(HEADER_SIZE, text_end)])
    image = rom[header.rom_start:header.rom_start + header.reloc_offset]

    def differing(fake_map):
        by_stock = relocate(image, full_stock, fake_map)
        by_patched = relocate(image, patched, fake_map)
        return sum(1 for i in range(0, len(image), 4) if by_stock[i:i + 4] != by_patched[i:i + 4])

    # An unaligned move also exposes words where a `lui` is shared by addresses that end
    # up either side of a 0x8000 boundary; the loader cannot get those right whatever
    # the order.
    unaligned = {frag: 0x80400000 + frag * 0x12340 + 0x7FF8 for frag in range(240)}
    return {
        "number": number, "id": fragment_id(section.addr), "vram": section.addr,
        "stock": len(stock), "built": len(built), "common": len(common_stock),
        "same_order": common_stock == common_built,
        "differing_words": differing(ALIGNED_MAP), "boundary_words": differing(unaligned),
        "stock_order_errors": len(order_errors(image, full_stock)),
        "built_order_errors": len(order_errors(image, patched)),
        "unpaired": len(unpaired),
        "stock_only": [e for e in stock if e not in built_set],
        "built_only_live": [e for e in built if e not in stock_set
                            and targets[e & OFFSET_MASK] in FRAGMENT_SPACE],
        "built_only_inert": sum(1 for e in built if e not in stock_set
                                and targets[e & OFFSET_MASK] not in FRAGMENT_SPACE),
    }


def verify(elf: Elf, rom: bytes) -> int:
    """Check the code entries rebuilt for every stock fragment against the ROM."""
    numbers = sorted(int(s.name[len(".fragment"):]) for s in elf.sections
                     if s.name.startswith(".fragment") and not s.name.endswith("_bss"))
    totals = {"stock": 0, "common": 0, "stock_only": 0, "built_only_live": 0, "built_only_inert": 0,
              "boundary_words": 0}
    mismatched, explained, reordered, stock_bad, built_bad = [], [], [], [], []
    for number in numbers:
        r = compare_text(elf, rom, number)
        totals["stock"] += r["stock"]
        totals["common"] += r["common"]
        totals["stock_only"] += len(r["stock_only"])
        totals["built_only_live"] += len(r["built_only_live"])
        totals["built_only_inert"] += r["built_only_inert"]
        totals["boundary_words"] += r["boundary_words"]
        # A fragment may only differ where the ROM lists a reference the ELF does not
        # have, i.e. where the disassembly holds a plain number instead of a symbol.
        if r["differing_words"]:
            (explained if r["stock_only"] else mismatched).append(number)
        if not r["same_order"]:
            reordered.append(number)
        notes = []
        if r["stock_only"]:
            notes.append(f"{len(r['stock_only'])} only in ROM (first {describe(r['stock_only'][0])})")
        if r["built_only_live"]:
            notes.append(f"{len(r['built_only_live'])} only in ELF (first {describe(r['built_only_live'][0])})")
        if r["unpaired"]:
            notes.append(f"{r['unpaired']} LO16 with no matching HI16")
        if r["stock_order_errors"]:
            notes.append(f"stock table fails the order check at {r['stock_order_errors']} words")
            stock_bad.append(number)
        if r["built_order_errors"]:
            notes.append(f"rebuilt table fails the order check at {r['built_order_errors']} words")
            built_bad.append(number)
        if r["differing_words"]:
            notes.append(f"{r['differing_words']} WORDS RELOCATE DIFFERENTLY")
        print(f"fragment{number:<3d} id {r['id']:#04x}  code entries {r['stock']:5d}  "
              f"reproduced {r['common']:5d}  {'; '.join(notes) or 'ok'}")
    print(f"code entries in ROM: {totals['stock']}; reproduced: {totals['common']} "
          f"({100 * totals['common'] / totals['stock']:.2f}%)")
    print(f"only in ROM (no relocation in the ELF): {totals['stock_only']}")
    print(f"only in ELF: {totals['built_only_live']} that affect loading, "
          f"{totals['built_only_inert']} main-segment or absolute (no effect)")
    print(f"fragments whose shared entries are in the stock order: "
          f"{len(numbers) - len(reordered)} of {len(numbers)}")
    print(f"words that differ only at a 0x8000 boundary under an unaligned move: "
          f"{totals['boundary_words']}")
    print(f"order check passed by the stock tables: {len(numbers) - len(stock_bad)} of {len(numbers)}"
          + (f" (failing: {stock_bad})" if stock_bad else ""))
    print(f"order check passed with rebuilt code entries: {len(numbers) - len(built_bad)} of {len(numbers)}"
          + (f" (failing: {built_bad})" if built_bad else ""))
    identical = len(numbers) - len(mismatched) - len(explained)
    print(f"fragments that relocate identically with the rebuilt code entries: "
          f"{identical} of {len(numbers)}")
    if explained:
        print(f"differ only where the ELF lacks a reference the ROM lists: {explained}")
    if mismatched:
        print(f"UNEXPLAINED differences: {mismatched}")
    return 1 if mismatched or built_bad or stock_bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("verify", help="rebuild every stock table and compare with the ROM")
    p.add_argument("elf", type=Path)
    p.add_argument("rom", type=Path)
    p = sub.add_parser("show", help="print one fragment's header")
    p.add_argument("rom", type=Path)
    p.add_argument("number", type=int)
    args = parser.parse_args()

    rom = args.rom.read_bytes()
    if args.command == "verify":
        return verify(Elf(args.elf), rom)

    headers = find_fragments(rom)
    header = headers[args.number - 1]
    table = read_table(rom, header)
    print(f"fragment {args.number}: rom {header.rom_start:#x}  entry jump {header.inst:#010x}")
    print(f"  relocOffset {header.reloc_offset:#x}  sizeInRom {header.size_in_rom:#x}  "
          f"sizeInRam {header.size_in_ram:#x}  relocations {len(table)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
