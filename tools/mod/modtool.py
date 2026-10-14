#!/usr/bin/env python3
"""Build steps for the rental editor's fragment and its hooks into the stock game.

The mod is one new fragment (id 0x40, linked at 0x85000000) stored in unused ROM
space. Stock functions are hooked without changing the size of anything: a hooked
function is overwritten in the ROM by a short thunk that jumps into the mod, and its
original body is assembled into the mod as `orig_<name>` so it can still be called.

mod/hooks.txt lists the hooks, one per line:

    boot    <function>  <target>    load the mod fragment, then continue at <target>
    jump    <function>  <target>    jump to <target>; the mod must already be loaded
    detour  <function>  <target>    as jump, but the rest of the stock function stays
    call    <function>  <target>    load the mod fragment for this one call of <target>

`boot` is for a screen the mod lives on: the fragment stays in the game's fragment
map, where that screen's `jump` and `detour` thunks find it, until the screen's pool
frees it. So a stock fragment with a `jump` or a `detour` in it needs a `boot` of its
own, in a function it runs once as it starts. `call` is for a screen that needs the mod
now and then: it loads a copy of its own, calls <target> in it, and puts the fragment
map back as it was. So it works whether or not another screen's copy is in memory, and
that copy's thunks go on working after it. Every call is another copy for the screen's
pool to free, so it is not for a function that runs every frame. Either way the copy is loaded once the hooked function's own fragment is in
memory, which is what lets the moved `orig_<name>` be relocated. Like a detour, a call
leaves the rest of the stock function where it is, so its function may have a jump
table.

Each target gets a slot in a jump table at the start of the fragment, so thunks
only ever need the fragment's load address, which they read from the game's
fragment map. Thunks contain no relocations.

A function with a jump table needs `detour`: the table still holds addresses inside
the stock function, so the moved copy's switch lands back in the stock body, which
therefore has to be left as it was past the thunk.

Stock code that the mod is not in memory for can be changed in place instead.
mod/stock_patches.txt lists single instructions to replace, in any fragment or in the
main segment, as mod/asm_patches.txt does for moved functions. Such an instruction may
not be one the fragment loader relocates, or one that names a symbol. A function the
decompilation has in C has no assembly to put the lines into, so its lines are
assembled each alone, and may not use the function's labels: a branch is `. + offset`.
The rest of a function hooked with `detour` or `call`, which stays where it is, can be
changed in place too.

The trainer pictures get a second directory, which gives each of a trainer's pictures a
number of its own; see gen_trainer_faces.py.

    modtool.py asm <hooks> <asm-dir> <out-dir>      write entry.s, moved.s and patched.s
    modtool.py inject --mod-elf E --game-elf G --rom R --hooks H --asm-dir A --out O
                      [--patched-obj P]
"""

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fragment_relocs as fr  # noqa: E402
import gen_trainer_faces  # noqa: E402
from check_rom import HOLE_END, HOLE_START  # noqa: E402

MOD_FRAGMENT_ID = 0x40
MOD_VRAM = fr.fragment_vram(MOD_FRAGMENT_ID)
SLOT_BASE = fr.HEADER_SIZE   # jump table starts right after the header
SLOT_SIZE = 8                # `j target` + delay slot
MOD_SECTION = ".modfrag"

MAIN_SECTION = ".text"       # the main segment, which is always in memory and never moves
PATCHED_PREFIX = "patched_"  # label of a stock function assembled with its in-place changes
CHECKSUM_OFFSET = 0x10

INSTRUCTION = re.compile(r"/\* [0-9A-F]+ ([0-9A-F]{8}) [0-9A-F]{8} \*/")
SECTION = re.compile(r"^\s*\.section\s+(\S+)")

# Registers
ZERO, V0, A0, A1, A2, A3, T0, T1, T9, SP, RA = 0, 2, 4, 5, 6, 7, 8, 9, 25, 29, 31

HOOK_KINDS = ("boot", "jump", "detour", "call")
KEEPS_BODY = ("detour", "call")   # past the thunk, the stock function stays as it was


def read_hooks(path: Path) -> list:
    hooks = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split("#")[0].split()
        if not fields:
            continue
        if len(fields) != 3 or fields[0] not in HOOK_KINDS:
            raise ValueError(f"{path}:{number}: expected '{'|'.join(HOOK_KINDS)} <function> <target>'")
        hooks.append({"kind": fields[0], "function": fields[1], "target": fields[2], "slot": len(hooks)})
    if not any(h["kind"] == "boot" for h in hooks):
        raise ValueError(f"{path}: a 'boot' hook is required")
    return hooks


def has_function_asm(asm_dir: Path, name: str) -> bool:
    """Whether the function is still assembly in the decompilation, with a file of its own."""
    return any(asm_dir.glob(f"nonmatchings/**/{name}.s"))


def lone_label(name: str, address: int) -> str:
    """The label of one changed instruction of a function that has no assembly file."""
    return f"{PATCHED_PREFIX}{name}_{address:08X}"


def find_function_asm(asm_dir: Path, name: str) -> Path:
    matches = sorted(asm_dir.glob(f"nonmatchings/**/{name}.s"))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}.s under {asm_dir}/nonmatchings, found {len(matches)}")
    return matches[0]


def function_extent(path: Path) -> tuple:
    """(start address, size in bytes) of the code in a splat function file."""
    section, addresses = ".text", []
    for line in path.read_text().splitlines():
        m = SECTION.match(line)
        if m:
            section = m.group(1)
            continue
        m = INSTRUCTION.search(line)
        if m and section == ".text":
            addresses.append(int(m.group(1), 16))
    if not addresses or addresses != list(range(addresses[0], addresses[0] + 4 * len(addresses), 4)):
        raise ValueError(f"{path}: could not read a contiguous function body")
    return addresses[0], 4 * len(addresses)


# --- assembly sources -----------------------------------------------------------------

ASM_HEADER = """\
# Generated by tools/mod/modtool.py. Do not edit.
.include "macro.inc"
.set noat
.set noreorder
.set gp=64
"""


def read_patches(path: Path) -> dict:
    """Instruction replacements for moved functions: function -> [(address, text)].

    Each line of the file is `<function> <address> <new instruction>`. A patch may
    only change an instruction in place; anything bigger belongs in C.
    """
    patches = {}
    if not path.exists():
        return patches
    for number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split("#")[0].split(None, 2)
        if not fields:
            continue
        if len(fields) != 3:
            raise ValueError(f"{path}:{number}: expected '<function> <address> <instruction>'")
        patches.setdefault(fields[0], []).append((int(fields[1], 16), fields[2].strip()))
    return patches


def apply_patches(name: str, source: str, patches: list) -> str:
    for address, text in patches:
        pattern = rf"^(\s*/\* [0-9A-F]+ {address:08X} [0-9A-F]{{8}} \*/\s+).*$"
        source, count = re.subn(pattern, lambda m: m.group(1) + text, source, flags=re.M)
        if count != 1:
            raise ValueError(f"{name}: no instruction at {address:#x} to patch")
    return source


def asm_home(path: Path) -> str:
    """Where the code of a splat function file lives, for a comment."""
    m = re.search(r"/fragments/(\d+)/", path.as_posix())
    return f"fragment {m.group(1)}" if m else "the main segment"


def renamed_function(asm_dir: Path, name: str, prefix: str, patches: list) -> str:
    """A stock function's assembly under the label `<prefix><name>`, with patches applied."""
    source = find_function_asm(asm_dir, name).read_text()
    renamed, count = re.subn(rf"^(\s*glabel\s+){re.escape(name)}\b", rf"\1{prefix}{name}",
                             source, flags=re.M)
    if count != 1:
        raise ValueError(f"{name}: expected one glabel")
    return apply_patches(name, renamed, patches)


def write_asm(hooks: list, asm_dir: Path, out_dir: Path, patches: dict = None,
              stock_patches: dict = None) -> None:
    patches = patches or {}
    stock_patches = stock_patches or {}
    hooked = {hook["function"] for hook in hooks}
    unknown = set(patches) - hooked
    if unknown:
        raise ValueError(f"patches for functions that are not hooked: {sorted(unknown)}")
    moved_away = set(stock_patches) & {hook["function"] for hook in hooks if hook["kind"] not in KEEPS_BODY}
    if moved_away:
        raise ValueError("stock patches for hooked functions, whose code runs from the mod; "
                         f"use asm_patches.txt: {sorted(moved_away)}")
    out_dir.mkdir(parents=True, exist_ok=True)

    entry = [ASM_HEADER, ".section .text", "",
             "# Fragment header; modtool.py inject fills it in.",
             f".space {fr.HEADER_SIZE:#x}", "",
             "# One slot per hook: thunks in the stock game jump here.",
             "glabel Mod_JumpTable"]
    for hook in hooks:
        entry += [f"    j           {hook['target']}", "     nop"]
    (out_dir / "entry.s").write_text("\n".join(entry) + "\n", newline="\n")

    moved = [ASM_HEADER]
    for hook in hooks:
        name = hook["function"]
        renamed = renamed_function(asm_dir, name, "orig_", patches.get(name, []))
        moved += [f"# --- {name}, moved out of {asm_home(find_function_asm(asm_dir, name))} ---",
                  ".section .text", renamed]
    (out_dir / "moved.s").write_text("\n".join(moved) + "\n", newline="\n")

    # Never linked: assembled only so that inject can lift the changed words out of it.
    patched = [ASM_HEADER]
    for name in sorted(stock_patches):
        if has_function_asm(asm_dir, name):
            renamed = renamed_function(asm_dir, name, PATCHED_PREFIX, stock_patches[name])
            patched += [f"# --- {name}, with instructions changed in place ---", ".section .text", renamed]
        else:
            patched += [f"# --- {name}, which is C in the decompilation: its changed instructions, each alone ---",
                        ".section .text"]
            for address, text in stock_patches[name]:
                patched += [f"glabel {lone_label(name, address)}", f"    {text}"]
    (out_dir / "patched.s").write_text("\n".join(patched) + "\n", newline="\n")


# --- thunks ---------------------------------------------------------------------------

def hi_lo(value: int) -> tuple:
    low = value & 0xFFFF
    return ((value >> 16) + (1 if low & 0x8000 else 0)) & 0xFFFF, low


def lui(rt, imm):
    return 0x3C000000 | (rt << 16) | imm


def addiu(rt, rs, imm):
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def lw(rt, offset, base):
    return 0x8C000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def sw(rt, offset, base):
    return 0xAC000000 | (base << 21) | (rt << 16) | (offset & 0xFFFF)


def jr(rs):
    return (rs << 21) | 0x08


def jal(target):
    return 0x0C000000 | ((target & 0x0FFFFFFF) >> 2)


def jalr(rs):
    return (rs << 21) | (RA << 11) | 0x09


def slot_offset(slot: int) -> int:
    return SLOT_BASE + SLOT_SIZE * slot


def jump_thunk(slot: int, map_entry: int) -> list:
    """Jump to a slot of the mod's jump table through the game's fragment map."""
    high, low = hi_lo(map_entry)
    return [lui(T9, high), lw(T9, low, T9), addiu(T9, T9, slot_offset(slot)), jr(T9), 0]


def boot_thunk(slot: int, fragment_load: int, rom_start: int, rom_end: int) -> list:
    """Load the mod fragment, then jump to one of its slots with the caller's arguments."""
    start_hi, start_lo = hi_lo(rom_start)
    end_hi, end_lo = hi_lo(rom_end)
    frame = 0x28
    return [
        addiu(SP, SP, -frame),
        sw(RA, 0x24, SP),
        sw(A0, frame + 0x0, SP), sw(A1, frame + 0x4, SP),   # the caller's argument area
        sw(A2, frame + 0x8, SP), sw(A3, frame + 0xC, SP),
        addiu(A0, ZERO, MOD_FRAGMENT_ID),
        lui(A1, start_hi), addiu(A1, A1, start_lo),
        lui(A2, end_hi),
        jal(fragment_load),
        addiu(A2, A2, end_lo),
        lw(RA, 0x24, SP),
        lw(A0, frame + 0x0, SP), lw(A1, frame + 0x4, SP),
        lw(A2, frame + 0x8, SP), lw(A3, frame + 0xC, SP),
        addiu(T9, V0, slot_offset(slot)),
        jr(T9),
        addiu(SP, SP, frame),
    ]


def call_thunk(slot: int, fragment_load: int, rom_start: int, rom_end: int, map_entry: int) -> list:
    """Load a copy of the mod fragment, call one of its slots with the caller's arguments,
    and put the fragment map's entry for the mod back as it was.

    The copy stays in the pool until the screen frees it, but nothing finds it again. The
    game clears a fragment's map entry when its memory is freed only if the entry still
    points at that memory (func_800046C0), so whatever the entry held before, another
    screen's copy included, is safe from this one's end.
    """
    start_hi, start_lo = hi_lo(rom_start)
    end_hi, end_lo = hi_lo(rom_end)
    map_hi, map_lo = hi_lo(map_entry)
    if map_lo in range(0x7FFC, 0x8000) or map_lo > 0xFFFB:
        raise ValueError("the fragment map's entry for the mod straddles a 64 KB boundary")
    frame, base, size = 0x30, 0x20, 0x24
    return [
        addiu(SP, SP, -frame),
        sw(RA, 0x2C, SP),
        sw(A0, frame + 0x0, SP), sw(A1, frame + 0x4, SP),   # the caller's argument area
        sw(A2, frame + 0x8, SP), sw(A3, frame + 0xC, SP),
        lui(T0, map_hi),
        lw(T1, map_lo, T0), lw(T0, map_lo + 4, T0),
        sw(T1, base, SP), sw(T0, size, SP),
        addiu(A0, ZERO, MOD_FRAGMENT_ID),
        lui(A1, start_hi), addiu(A1, A1, start_lo),
        lui(A2, end_hi),
        jal(fragment_load),
        addiu(A2, A2, end_lo),
        lw(A0, frame + 0x0, SP), lw(A1, frame + 0x4, SP),
        lw(A2, frame + 0x8, SP), lw(A3, frame + 0xC, SP),
        addiu(T9, V0, slot_offset(slot)),
        jalr(T9),
        0,
        lw(T1, base, SP), lw(T9, size, SP),
        lui(T0, map_hi),
        sw(T1, map_lo, T0), sw(T9, map_lo + 4, T0),
        lw(RA, 0x2C, SP),
        jr(RA),
        addiu(SP, SP, frame),
    ]


def thunk(hook: dict, fragment_load: int, rom_start: int, rom_end: int, map_entry: int) -> list:
    if hook["kind"] == "boot":
        return boot_thunk(hook["slot"], fragment_load, rom_start, rom_end)
    if hook["kind"] == "call":
        return call_thunk(hook["slot"], fragment_load, rom_start, rom_end, map_entry)
    return jump_thunk(hook["slot"], map_entry)


# --- the mod fragment -----------------------------------------------------------------

def pack_fragment(elf: fr.Elf) -> bytes:
    """The mod fragment as stored in ROM: header, contents, relocation table."""
    section = elf.by_name[MOD_SECTION]
    if section.addr != MOD_VRAM:
        raise ValueError(f"{MOD_SECTION} is linked at {section.addr:#x}, expected {MOD_VRAM:#x}")
    image = bytearray(elf.contents(section))
    if len(image) % 16:
        raise ValueError("fragment contents are not padded to 16 bytes")
    bss = elf.by_name.get(MOD_SECTION + "_bss")
    bss_size = bss.size if bss else 0
    if bss and bss_size and bss.addr != MOD_VRAM + len(image):
        raise ValueError("BSS must start where the relocation table goes")

    entries, unpaired = fr.build_entries(elf.relocations(MOD_SECTION), MOD_VRAM, bytes(image),
                                         fr.HEADER_SIZE)
    if unpaired:
        raise ValueError("LO16 relocations with no HI16 on their register at "
                         + ", ".join(f"{MOD_VRAM + o:#x}" for o in unpaired))

    reloc_offset = len(image)
    entry_point = MOD_VRAM + slot_offset(0)
    table = [(fr.R_MIPS_26 << 24) | 0] + entries   # the header's own jump
    packed_table = fr.pack_table(table)
    size_in_rom = (reloc_offset + len(packed_table) + 15) & ~15
    size_in_ram = reloc_offset + ((bss_size + 15) & ~15)
    image[:fr.HEADER_SIZE] = fr.pack_header(entry_point, reloc_offset, size_in_rom, size_in_ram)

    errors = fr.order_errors(bytes(image), table)
    if errors:
        raise ValueError("the loader would mis-relocate " + ", ".join(f"{MOD_VRAM + o:#x}" for o in errors))

    # The mod can load anywhere, so one `lui` must never serve two of its own addresses.
    # (Moved stock code may do this for stock data; that is as safe as it is in the
    # unmodified game, where the same code meets the same load addresses.)
    span = range(MOD_VRAM, MOD_VRAM + fr.FRAGMENT_SPAN)
    shared = {at: addresses for at, addresses in fr.shared_high_halves(bytes(image), table).items()
              if any(a in span for a in addresses)}
    if shared:
        raise ValueError("one `lui` is shared by several mod addresses; go through a pointer instead: "
                         + "; ".join(f"{MOD_VRAM + at:#x} -> " + ", ".join(f"{a:#x}" for a in addresses)
                                     for at, addresses in sorted(shared.items())))
    return bytes(image) + packed_table.ljust(size_in_rom - reloc_offset, b"\0")


# --- injection ------------------------------------------------------------------------

def update_checksum(rom: bytearray) -> None:
    import ipl3checksum

    kind = ipl3checksum.detectCIC(rom)
    if kind is None:
        raise ValueError("could not identify the ROM's boot code")
    first, second = kind.calculateChecksum(rom)
    struct.pack_into(">II", rom, CHECKSUM_OFFSET, first, second)


def stock_fragment(game_elf: fr.Elf, address: int) -> tuple:
    """(number, section) of the stock fragment that holds `address`."""
    for section in game_elf.sections:
        m = re.fullmatch(r"\.fragment(\d+)", section.name)
        if m and section.addr <= address < section.addr + section.size:
            return int(m.group(1)), section
    raise ValueError(f"{address:#x} is not in any fragment")


def stock_home(game_elf: fr.Elf, rom: bytes, address: int) -> tuple:
    """Where stock code is: (the ROM offset of `address`, the ROM offsets around it that
    the game relocates as it loads them). The main segment is not relocated."""
    main = game_elf.by_name[MAIN_SECTION]
    if main.addr <= address < main.addr + main.size:
        return game_elf.symbol("text_ROM_START") + address - main.addr, set()
    number, section = stock_fragment(game_elf, address)
    stock_rom = game_elf.symbol(f"fragment{number}_ROM_START")
    table = fr.read_table(rom, fr.read_header(rom, stock_rom))
    return stock_rom + address - section.addr, {stock_rom + (entry & fr.OFFSET_MASK) for entry in table}


def apply_stock_patches(rom: bytearray, game_elf: fr.Elf, patched: fr.Elf, stock_patches: dict,
                        asm_dir: Path, hooks: list = ()) -> int:
    """Writes the changed instructions of mod/stock_patches.txt over the stock ones.

    `patched` is the object assembled from patched.s. Only the words at the listed
    addresses are taken from it, and none of them may need relocating: not by the
    linker (the object is never linked) and not by the game's fragment loader. Nor
    may one be under a hook's thunk.
    """
    if not stock_patches:
        return 0
    code = patched.contents(patched.by_name[".text"])
    unlinked = {r.offset for r in patched.relocations(".text")}
    thunks = {hook["function"]: 4 * len(thunk(hook, 0, 0, 0, 0)) for hook in hooks}
    count = 0
    for name, patches in sorted(stock_patches.items()):
        start = game_elf.symbol(name)
        whole = has_function_asm(asm_dir, name)
        if whole:
            if function_extent(find_function_asm(asm_dir, name))[0] != start:
                raise ValueError(f"{name}: assembly and ELF disagree on its address")
            base = patched.symbol(PATCHED_PREFIX + name)
        rom_start, loaded = stock_home(game_elf, rom, start)
        for address, _ in patches:
            if not start + thunks.get(name, 0) <= address < start + 0x10000:
                raise ValueError(f"{name}: {address:#x} is not in the function, or is under its hook's thunk")
            at = base + address - start if whole else patched.symbol(lone_label(name, address))
            rom_at = rom_start + address - start
            if at in unlinked or rom_at in loaded:
                raise ValueError(f"{name}: the instruction at {address:#x} is relocated, "
                                 "so it cannot be changed in place")
            rom[rom_at:rom_at + 4] = code[at:at + 4]
            count += 1
    return count


def split_address(table: list, start: int, end: int):
    """The offset of a HI16 or LO16 entry in [start, end) whose other half is outside it,
    or None. In a table each HI16 is directly followed by its LO16s."""
    group = []
    for entry in table + [0]:
        kind, offset = (entry >> 24) & 0x7F, entry & fr.OFFSET_MASK
        if kind != fr.R_MIPS_LO16:
            inside = [o for o in group if start <= o < end]
            if inside and len(inside) != len(group):
                return inside[0]
            group = []
        if kind in (fr.R_MIPS_HI16, fr.R_MIPS_LO16):
            group.append(offset)
    return None


def inject(mod_elf: fr.Elf, game_elf: fr.Elf, rom: bytearray, hooks: list, asm_dir: Path,
           patched: fr.Elf = None, stock_patches: dict = None) -> dict:
    fragment = pack_fragment(mod_elf)
    rom_start, rom_end = HOLE_START, HOLE_START + len(fragment)
    if rom_end > HOLE_END:
        raise ValueError(f"mod fragment is {len(fragment):#x} bytes; only {HOLE_END - HOLE_START:#x} fit")
    if rom[HOLE_START:HOLE_END].count(0xFF) != HOLE_END - HOLE_START:
        raise ValueError("the ROM hole is not empty; inject into an unmodified build")
    rom[rom_start:rom_end] = fragment

    # Slots must be where the thunks expect them.
    for hook in hooks:
        want = MOD_VRAM + slot_offset(hook["slot"])
        (inst,) = struct.unpack_from(">I", fragment, slot_offset(hook["slot"]))
        if fr.jump_target(inst, MOD_VRAM) != mod_elf.symbol(hook["target"]):
            raise ValueError(f"slot {hook['slot']} at {want:#x} does not jump to {hook['target']}")

    map_entry = game_elf.symbol("D_800CC630") + MOD_FRAGMENT_ID * 8
    fragment_load = game_elf.symbol("Fragment_Load")

    # The stock fragments the mod stays loaded for: those with a `boot` hook.
    homes = {stock_fragment(game_elf, game_elf.symbol(hook["function"]))[0]
             for hook in hooks if hook["kind"] == "boot"}

    # Each stock fragment with hooks in it: its table as it was, and where its thunks went.
    hooked = {}
    for hook in hooks:
        start, size = function_extent(find_function_asm(asm_dir, hook["function"]))
        if start != game_elf.symbol(hook["function"]):
            raise ValueError(f"{hook['function']}: assembly and ELF disagree on its address")
        number, stock = stock_fragment(game_elf, start)
        if hook["kind"] in ("jump", "detour") and number not in homes:
            raise ValueError(f"{hook['function']} is in fragment {number}, where no `boot` hook has "
                             f"loaded the mod for a `{hook['kind']}` hook to find")
        stock_rom = game_elf.symbol(f"fragment{number}_ROM_START")
        if number not in hooked:
            header = fr.read_header(rom, stock_rom)
            hooked[number] = {"rom": stock_rom, "header": header, "table": fr.read_table(rom, header),
                              "ranges": []}
        table = hooked[number]["table"]
        words = thunk(hook, fragment_load, rom_start, rom_end, map_entry)
        if 4 * len(words) > size:
            raise ValueError(f"{hook['function']} is {size} bytes, too small for a {4 * len(words)}-byte thunk")
        offset = start - stock.addr
        body = struct.pack(f">{len(words)}I", *words)
        if hook["kind"] in KEEPS_BODY:
            # Only the thunk's bytes change. An address the loader relocates in two halves
            # must not have one of them there and the other in the body that stays.
            split = split_address(table, offset, offset + len(body))
            if split is not None:
                raise ValueError(f"{hook['function']}: the thunk would split an address the loader "
                                 f"relocates in two halves, at {stock.addr + split:#x}")
        else:
            body = body.ljust(size, b"\0")
        rom[stock_rom + offset:stock_rom + offset + len(body)] = body
        hooked[number]["ranges"].append((offset, offset + len(body)))

    # The thunks have no relocations, so the stock entries for those bytes just go.
    removed = 0
    for stock in hooked.values():
        table = stock["table"]
        kept = fr.merge_table(table, [], stock["ranges"])
        table_at = stock["rom"] + stock["header"].reloc_offset
        rom[table_at:table_at + 4 * (len(table) + 1)] = fr.pack_table(kept).ljust(4 * (len(table) + 1), b"\0")
        removed += len(table) - len(kept)

    patched_count = apply_stock_patches(rom, game_elf, patched, stock_patches or {}, asm_dir, hooks)
    pictures = gen_trainer_faces.install(rom)

    update_checksum(rom)
    return {"rom_start": rom_start, "rom_end": rom_end, "size": len(fragment),
            "relocations": struct.unpack_from(">I", fragment, len(mod_elf.contents(mod_elf.by_name[MOD_SECTION])))[0],
            "removed": removed, "hooks": len(hooks), "patched": patched_count,
            "pictures": pictures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("asm", help="write the generated assembly sources")
    p.add_argument("hooks", type=Path)
    p.add_argument("asm_dir", type=Path)
    p.add_argument("out_dir", type=Path)
    p = sub.add_parser("inject", help="write the mod fragment and hook thunks into a ROM")
    p.add_argument("--mod-elf", type=Path, required=True)
    p.add_argument("--game-elf", type=Path, required=True)
    p.add_argument("--rom", type=Path, required=True)
    p.add_argument("--hooks", type=Path, required=True)
    p.add_argument("--asm-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--patched-obj", type=Path, help="patched.s, assembled")
    args = parser.parse_args()

    hooks = read_hooks(args.hooks)
    stock_patches = read_patches(args.hooks.with_name("stock_patches.txt"))
    if args.command == "asm":
        write_asm(hooks, args.asm_dir, args.out_dir,
                  read_patches(args.hooks.with_name("asm_patches.txt")), stock_patches)
        return 0

    if stock_patches and not args.patched_obj:
        parser.error("stock_patches.txt needs --patched-obj")
    rom = bytearray(args.rom.read_bytes())
    info = inject(fr.Elf(args.mod_elf), fr.Elf(args.game_elf), rom, hooks, args.asm_dir,
                  fr.Elf(args.patched_obj) if stock_patches else None, stock_patches)
    args.out.write_bytes(rom)
    print(f"mod fragment: {info['size']:#x} bytes at ROM {info['rom_start']:#x}-{info['rom_end']:#x}, "
          f"{info['relocations']} relocations")
    print(f"hooks: {info['hooks']} thunks written, {info['removed']} stock relocation entries removed")
    print(f"stock code: {info['patched']} instructions changed in place")
    print(f"trainer pictures: {info['pictures']} numbered, in a directory at ROM {gen_trainer_faces.DIRECTORY_ROM:#x}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
