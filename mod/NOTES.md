# Rental editor — working notes

Reverse-engineering notes for the rental editor mod. Addresses are for the US ROM
(sha1 `d8343e69a7dc63b869cf6361d87cde64444281d3`). Each fact is tagged:
**[C]** confirmed in source, **[I]** inferred and still to be verified at runtime.

Base: `michiiik/pokestadiumgs` pinned at `e06da865` (branch `rental-editor`).
Plan: `C:\Users\Alex\.claude\plans\i-want-to-build-delightful-lecun.md`.

## Status

- **M0 done.** The stock build matches the original ROM and boots.
- **M1 mostly done.** See "Open questions" for what is left.
- **M2 done in BizHawk.** The mod fragment loads from the entry screen, and leaving and
  re-entering the screen is clean (fragment map entry 0x40 is cleared on exit and
  reappears at the same address).
- **M3 and most of M4 done in BizHawk.** EDIT on a rental's ENTER menu opens a
  full-width editor window over the party box; the stock detail panel stays visible below
  it as a live preview. One cursor moves between three columns: the four moves (and the
  level beneath them), DVs for Attack/Defense/Speed/Special, and Stat Exp for all five
  stats. A on a move opens a list of the species' legal moves with type, power, accuracy
  and PP. A on a number grabs it: up/down step, left/right step further, L/R jump to the
  ends. Stat Exp steps between the 64 values that change the stat. Level is held to the
  rule set's range.
  - Checked: Attack DV 15 and Stat Exp 65535 took Abra's Attack from 116 to 138; level 90
    recalculated every stat; closing the editor restores the party box.
  - Checked through to battle: an Abra edited to 10/10/10/10 with Hidden Power in its
    fourth slot fights as a shiny with 213 HP and Psychic, Ice Punch, Hidden Power and
    Swagger.
- **What DVs decide besides stats** is shown on the editor's title row, each only when it
  applies: the gender symbol beside the name, `SHINY`, Unown's `LETTER`, and Hidden
  Power's type and power when the Pokémon knows the move. The move list shows Hidden
  Power's real type and power too. When a DV change alters the look (shiny, Unown's
  letter, Smeargle's paint) the 3D model and the list icon are reloaded.
  - Checked: Abra at 10/10/10/10 turns shiny in the panel, the list and the party box,
    with Hidden Power Grass 69, and it is shiny in battle too; Attack DV 0 flips it to
    female; Unown at 0/14/14/15 becomes G with Hidden Power Poison 50.
- **M5 done in BizHawk.** Both ways of registering a team offer EDIT: "OK to Register"
  after picking in Free Battle, and Register POKéMON on the entry screen ("Rental Only
  (register)"), which is the same picker.
  - Checked: the shiny Abra above was registered, the console reset
    (`client.reboot_core()`), and the set chosen from Registered POKéMON. The record came
    back with the same moves, PP, DVs `0xAAAA`, Stat Exp and level, the rental flag still
    set, and the stats recalculated to the same values.
- Held items are left to the stock ITEM entry, which already handles rentals.
- Nothing has been run on standalone ares or hardware yet.
- Known gaps: an edit lives in the list cell, so scrolling the rental far away and back
  before entering it loses the edit. The stock detail panel and the battle menu label
  Hidden Power as Normal, as they do in the unmodified game.

## Building

The build runs in WSL (Ubuntu). From the repo root inside WSL:

    python3 tools/mod/check_rom.py <path-to-rom>   # verify + install baserom
    tools/mod/wsl_build.sh init                    # first time
    tools/mod/wsl_build.sh                         # stock ROM, must match the original
    tools/mod/wsl_build.sh mod                     # build/pokestadiumgs-us-mod.z64
    tools/mod/wsl_build.sh pull-asm                # copy asm/ back for reading
    python3 -m unittest discover -s mod/tests      # 63 tests

`wsl_build.sh` mirrors the sources to `~/stadium2-build` (native ext4) because building
on the Windows drive is slow, then copies the ROMs, map and ELF back into `build/`.

The fork's own sources are not modified. `wsl_build.sh mod` compiles `mod/src/*.c` with
the game's compiler (IDO 7.1), links them at `0x85000000` against the game's symbols, and
`tools/mod/modtool.py inject` writes the result into a copy of the stock ROM.

## How the mod hooks the game

- The mod is fragment id 0x40, stored at ROM `0x16061C0`. Its first 0x20 bytes are the
  header, followed by a jump table with one `j target` slot per line of `mod/hooks.txt`.
- A hooked stock function is overwritten in the ROM by a thunk and its relocation
  entries are dropped. Its original body is assembled into the mod as `orig_<name>`.
  - `jump` thunk, 5 instructions: read the mod's base from the fragment map
    (`D_800CC630 + 0x40 * 8`), add the slot offset, `jr`.
  - `boot` thunk, 20 instructions: save the arguments, `Fragment_Load(0x40, start, end)`,
    restore, `jr` to a slot of the returned base. Thunks contain no relocations.
- The boot hook is `func_8130251C`, fragment 14's setup. It runs once per screen, before
  the screen takes the rest of the main pool, and the pool frees the mod on exit.
- Only asm functions can be hooked so far (the tool takes their size and body from
  `asm/us/nonmatchings`). Hooking a decompiled function needs its body from elsewhere.
- `mod/asm_patches.txt` changes single instructions in a moved function, by address.
- `modtool.py inject` refuses to build a fragment the loader could get wrong: every
  LO16 must have a HI16, the table must pass the order check, and no `lui` may serve two
  addresses inside the mod. Hence `Edit_GetState` in `mod/src/state.s`: C code reaches
  the editor's state only through that pointer.

In the Free Battle path the mod loads at `0x80253290`; fragment 14 is at `0x80154DA0`.

## In-memory Pokémon record (0x58 bytes)

Recovered from the GB <-> internal converters in `src/615D0.c`
(`func_80061124` Gen 2 party struct -> internal, `func_800614EC` the reverse,
`func_80060FF8` / `func_800613F8` the Gen 1 pair). Size confirmed by
`func_82B062F8` (`_bzero(arg0, 0x58)`). **[C]** for offsets, **[I]** for the names.

| Offset | Size | Field |
|---|---|---|
| 0x00 | u8 | species |
| 0x01 | u8 | held item |
| 0x02 | u8[4] | moves |
| 0x06 | u16 | OT ID |
| 0x08 | u32 | experience |
| 0x0C | u16 x5 | stat exp: HP, Attack, Defense, Speed, Special |
| 0x16 | u16 | DVs (Atk/Def nibbles, Spd/Spc nibbles) |
| 0x18 | u8[4] | PP |
| 0x1C | u8 | happiness |
| 0x1D | u8 | level |
| 0x1E | u8 | flags: bit 0 forces current HP to 0 (`func_800616BC`); bit 2 (0x04) marks a rental |
| 0x20 | u8 | pokerus |
| 0x21 | u8[2] | caught data |
| 0x24 | u8 | status |
| 0x26 | u16 | current HP |
| 0x28 | u16 x6 | max HP, Attack, Defense, Speed, Sp. Atk, Sp. Def |
| 0x34 | char[12] | nickname, plain ASCII; rentals get the species name |
| 0x40 | char[12] | second name, probably OT |
| 0x4C | u8[11] | trailing bytes copied as a block (`func_80061248`) |

Stat calculation: `func_8006183C(stat, species, statExp, level, dvs)` (still asm).
`StatExpSqrt` is at `0x8006175C`.

## Rental data in ROM

Source: `pret/pokestadium` `oldnotes/utils/extractrostertbltbl.c` and `json2rostertbl.c`.

- Table of tables at ROM `0x1708000`; table count/pointers start at `+0xC`. **[I]**
- Each table: `u8 count`, 3 zero bytes, then records.
- Rental tables: Little Cup (86 entries, L5), Poké Cup (246, L50), Prime Cup (246 and 248, L100).

Rental record, 24 bytes, big-endian:

| Offset | Field |
|---|---|
| 0x00 | level |
| 0x01 | species |
| 0x02 | item (always 0 for rentals) |
| 0x03 | unknown |
| 0x04 | moves[4] |
| 0x08 | unknown |
| 0x09 | happiness |
| 0x0A | stat exp x5 (u16) |
| 0x14 | DVs (u16) |
| 0x16 | unknown x2 |

Rental records carry no nickname or OT; those are filled in when the record is expanded.

## Fragments (overlays)

Same system as Stadium 1 (`pret/pokestadium` `src/memmap.c`, `include/macros.h`).

- Header, 0x20 bytes: two entry instructions, `"FRAGMENT"`, `headerSize`, `relocOffset`,
  `sizeInRom`, `sizeInRam`.
- Fragment ID = `((vram & 0x0FF00000) >> 20) - 0x10`, so ID `n` lives at `0x81000000 + n * 0x100000`.
- `Fragment_Load(id, romStart, romEnd)` at `0x800047F8`; `Fragment_LoadAndCall` at `0x80064CE8`.
  The caller supplies the ROM range, so a new fragment needs no table entry. **[C]**
- Relocation table at `relocOffset`: `u32 count`, then `(flag << 31) | (type << 24) | offset`.
  Types: `R_MIPS_32` (2), `R_MIPS_26` (4), `R_MIPS_HI16` (5), `R_MIPS_LO16` (6). **[C]**
  - *Every* relocation is listed. The flag marks a target outside the fragment itself
    (main segment, another fragment, an absolute value). The loader masks it off and
    rebases whatever address falls inside a loaded fragment.
  - Order is the original source order with each HI16 directly followed by its LO16s, not
    address order. It matters: the loader keeps one pending HI16 per register and applies
    each LO16 to the pending HI16 of its base register.
- BSS starts at `relocOffset`: after relocating, the loader zeroes from there to
  `sizeInRam`, wiping the table. Fragment 15 has `sizeInRam` (0x410) below `sizeInRom`
  (0x500). So a stock fragment cannot grow without colliding with its own BSS symbols.
- The header's entry jump has its own table entry (`26` at offset 0).
- Known weakness of the loader: a `lui` shared by two addresses that land either side of
  a 0x8000 boundary after loading gets the wrong upper half for one of them. The stock
  game has 64–91 such sites under an arbitrary move; keep new code to one address per `lui`.

`tools/mod/fragment_relocs.py` builds tables from the relocations the linker keeps
(`--emit-relocs`). `verify` on the stock ROM: 118,976 of 119,048 code entries reproduced;
the rebuilt entries pass an independent order check in 88 of 88 fragments, as do all 88
stock tables; 84 of 88 relocate byte-for-byte like stock. Fragments 26, 31, 44 and 79
differ only where the disassembly has a plain number in place of a symbol. Stock data
pointers are mostly not symbolic either, so stock tables are patched with `merge_table`
rather than rebuilt.

**Hook design that follows from this:** leave fragment 14 the same size. To change one of
its functions, move that function into the mod fragment and overwrite the original with a
short jump (rebuilding only that range of the table). The mod fragment is loaded with
`Fragment_Load`, which returns its base, so the first jump into it needs no relocation.
- IDs in use (from `MatandoYT/pokestadiumgs`): 0x00, 0x01, 0x03, 0x04, 0x06–0x0C, 0x10–0x25, 0x2F,
  0x31–0x34, 0x50–0x5C, 0x6C–0x7D, 0x9B, 0x9C, 0x9E, 0x9F, 0xE0–0xEE. `0x40` is free. **[I]**

## ROM layout

- Main segment `0x1000–0xA8A80`, vram `0x80000400`.
- Fragments 1–88 at `0xA8A80–0x437610`; the first megabyte is covered by the header CRC.
- `0x437610–0x4000000` is one asset blob that must not move.
- `0x16061C0–0x1638000` is `0xFF` padding (204,352 bytes): home for the mod fragment. **[C]**
  `check_rom.py` verifies it on the real ROM.

## Game flow

`Game_Thread` (`src/65820.c`) switches on the game state in `D_8009DE94`:
17 boot (fragment 15 logos, fragment 67 intro), 2 Game Pak Check / "Please Select",
3 White City map, **16 Free Battle setup and entry**, **13 the battle loop**.

- State 16 (`func_80068E14`): rule select, stage select, then the entry screen in
  **fragment 14** with shared UI fragments 11 and 18 loaded. **[C]** from the live fragment map.
- State 13 (`func_800684F0`, tags `btpc`/`btlp`): fragment 24 (pre-battle selection, mode
  `0x10000`), fragment 20, fragment 12, **fragment 79 (battle)**, fragment 20 again, loop.
- `Fragment_LoadAndCall` frees the fragment (`main_pool_try_free`) after its entry returns.
- The second ROM argument to `Fragment_Load*` is the *next* fragment's `ROM_START`.

Fragment 24 is therefore not the picker. It does contain `func_82B062F8`, which zeroes a
0x58-byte record and sets a level from `D_82B0865C[n]`.

## Fragment 14 (vram 0x81300000) — entry screen and rental picker

Text 0x81300020–0x81311D30, data to 0x81312470, rodata/relocs to 0x81314DE0, then bss.
Runs at `0x80154DA0` in the Free Battle path (size 0x319D0).

The entry screen offers **Registered Pokémon / Register Pokémon / Rental Only**; the last
opens the picker (box tabs `P`, `1`–`14`, `R`; 3 rows x 4 cells visible).

- Screen state: `D_81317800`, at least 0x13800 bytes. `state + 0x6C` points at the record
  of the Pokémon currently open in the detail panel. **[C]** at runtime.
- `func_8130251C` opens archive 0xB (`func_800356CC(0xB)` → `BinArchive_Open`), picks the
  rental table with `func_80071B20(archive, func_80071914(rule))`, then `func_81300830(state, table, …)`.
- `func_8130785C(state, row, rowIndex)` fills one row of four cells:
  - Game Pak / registered sources: `func_8006218C` (open), `func_8006236C`, `func_80062390`
    (read one Pokémon), `func_800619E8`, `func_80061F44`, `func_80062304` (close).
  - Rentals: `func_80071E48(cell, table + 4 + index * 0x18)`, then `cell[0x1E] |= 4`.
  - Unless the rule's flag word (`…->0x940->0x40`, bit 26) is set, every cell's item is cleared.
- Cell, 0xCE8 bytes: `+0x00` the 0x58-byte record, `+0x58` source (5 = rental, else box + 1),
  `+0x59` tab, `+0x5A` index in source, `+0x5B` species, `+0x60` icon. A row is four cells
  plus 0x10 bytes (0x33B0). The party box holds cells of the same shape
  (`party + 0x20 + n * 0xCE8`), so every record the detail panel is given starts a cell.
- The icon is rendered into the cell by `func_8004D878(cell + 0x60, 0, cell)` when the
  cell is filled, and drawn from there; entering a Pokémon copies the whole cell.
- Pressing A on a cell opens the detail panel (stats, four moves) and the menu
  **ENTER: Yes / No / ITEM**, plus "C to check TM". This menu is where EDIT goes.
  The game already lets a rental be given a held item through ITEM.
- The whole fragment is shared: its text bank (0xF) holds the entry, registration
  ("OK to Register", "Rental Only (register)") and cup strings, so one hook covers
  Free Battle, team registration and the cups.

Detail panel object (`fragment14_104FC0.c`), the first argument of everything below:

| Offset | Field |
|---|---|
| 0x08, 0x0A | x, y (s16) |
| 0x34 | state: 0 closed, 1 menu active, 3 closing after a choice, 4 item list open |
| 0x35 | mode: 0 ENTER, 1 EXCHANGE, 2+ view only |
| 0x36 | cursor (s8): 0 Yes, 1 No, 2 ITEM |
| 0x24 | the word at record + 0x58 (source, tab, index, species) when it was opened |
| 0x39 | chosen item |
| 0x5C | item list object, NULL when the rules allow no items |
| 0x68 | the 3D model shown in the panel |
| 0x6C | the Pokémon record being shown |
| 0x70 | model timer: counts down a frame at a time, and at 0 `func_80042F94(model, record)` loads the model. `func_8130EA8C` sets it to 2 when the panel is given a new record |

The panel is opened by `func_8130EB04(panel, controller, record, mode, …)`: mode 0 from the
list once a cell is chosen (`func_81308F54`), 2 while browsing the list (`func_8130B620`),
1 and 3 from the party box (`func_81303D60`, `func_813037F0`).

| Function | Role |
|---|---|
| `func_8130DEB8` | draws the detail panel (stats, moves); labels from text bank 0xD |
| `func_8130DA04` | draws the ENTER menu; items at `x + 0x191 + 0x45`, `y + 0x26 + 0x15 * n` |
| `func_8130CEAC` | number of menu items: 2, or 3 when an item list exists (C) |
| `func_8130CE3C` | whether "Yes" is greyed out (C) |
| `func_8130EC9C` | probably the menu's input handler (uses the cursor; asm) |
| `func_8130F2C4` | panel update, a jump table on the state (hand-maintained asm) |
| `func_8130F578` | result once closed: cursor + 1 (C) |

Text bank 0xF entries: 1 ENTER, 2 EXCHANGE, 4 Yes, 5 No, 6 ITEM, 7 "to check TM",
8 "to quit", 9 "No item", 0x19 RENTAL POKéMON, 0x25–0x2A First…Sixth POKéMON.

Text drawing as the stock code does it: `gSPDisplayList(D_800D0510++, D_80094F50)`,
`func_800498C4()`, `func_800496A4(4, 1)`, `func_8004972C(r, g, b, a)`,
`func_800495BC(x, y, string)`, `func_800499EC()`. Strings are plain ASCII.

The chosen record is copied into the party when "Yes" is confirmed; in the Free Battle
path the party copy sits at `state + 0x15390`. The battle then works from its own copies
(six of them, one at `0x800D1C60`). Nothing re-reads the rental table.

### Redrawing

The screen does not repaint every frame. Each frame a widget registers its rectangle with
`func_81600A34(ctx, key, dirty, x, y, w, h)`, and `func_81600DA8(ctx, key)` then says
whether to draw it: when it is dirty, was dirty last frame (two framebuffers), or is new.
`func_8130F2C4` registers the panel's regions:

| Key | Region | Dirty when |
|---|---|---|
| `panel` | detail panel | `panel->0x00` is nonzero (then cleared) |
| `panel + 1` | ENTER menu box | `state == 1`, i.e. every frame the menu is open |
| `panel + 3` | Pokémon model | always |
| `panel + 4` | "check TM" popup | `panel->0x38 >= 0` |

Drawing outside a registered region leaves ghosts. After changing the record, set
`panel->0x00 = 1` to repaint the detail panel.

`func_81600B30` settles the regions each frame: a region whose rectangle changed is
dirty, and when a region stops being registered, everything that overlapped it is marked
dirty. So an overlay needs no cleanup: stop registering it and the screen repaints what
it covered. The editor window works this way. `Mod_EnterMenuInput`, which runs in the
update pass, registers it every frame it is open, keyed by the address of the editor's
state; `Mod_DrawEnterMenu` draws it when `func_81600DA8` says so. It is drawn from the
ENTER menu's draw call, which comes after the party box and list, so it lands on top.

UI library pieces used (fragment 11):

| Function | Role |
|---|---|
| `func_816048E0(x, y, w, h)` | framed window in the game's style; inside is `x + 8`, `y + 8`, `w - 19`, `h - 19` |
| `func_816073A0(rect)` / `func_81607408()` | clip to a window's inside / to the full screen |
| `Gfx_FillRectRgb(x, y, w, h, r, g, b)` | filled rectangle, after `gSPDisplayList(D_800D0510++, D_80094D90)` |
| `func_80049148(font, 1, string)` | width of a string |

The font has no `<` or `>` glyphs. The ENTER box's inside is `x + 0x198`, `y + 9`,
129 x 128, colour `#3333F8`; the editor paints its key hints there.

### Rules

`*(Rules **)(D_8133197C + 0x940)` is the rule set in force (in the main segment; Anything
Goes is at `0x8009F5C4`). `+0x14`: 32-byte bitmask of allowed species. `+0x36`/`+0x37`:
minimum and maximum level (0 and 100 for Anything Goes). `+0x38` (u16): cap on combined
levels (600). `+0x40`: flag word; bit 26 allows held items.

### Input

`func_8130EC9C(panel)` reads `D_800CE060[panel->0x37]` (0x28 bytes per controller):
`+0x08` held buttons, `+0x0C` newly pressed. A on cursor 2 opens the item list; A on
anything else, or B, closes the menu with result `cursor + 1`. Up/down move the cursor
within `func_8130CEAC`'s count. C buttons open the "check TM" popup for a move.

## Pokémon helpers (main segment)

| Address | Role |
|---|---|
| `func_80071E48(mon, rental)` | expand a 24-byte rental entry into a 0x58-byte record (asm, `src/728D0.c`) |
| `func_80071BB8(mons, roster)` | expand up to six roster entries (CPU teams) |
| `func_800619E8(mon)` | level from experience, then all six stats |
| `func_8006183C(stat, species, statExp, level, dvs)` | one stat; 0 HP, 1 Atk, 2 Def, 3 Spd, 4 SpA, 5 SpD |
| `func_80061B88(species, level)` | experience needed for a level |
| `func_80061ED0(species, exp)` | level for an experience total |
| `func_80061F44(mon)` | current HP = max HP, clear status, refill PP |
| `func_80062EB0(move, ppUpBits)` | max PP for a move |
| `func_8004B7A4(species)` | species name string |
| `func_80062CE0(move)` | move name string (text bank 6) |
| `func_80062D20/D5C/D98/DD4/E10/F2C(move)` | effect, power, type, accuracy, PP, effect chance |
| `func_80062EB0(move, ppByte)` | PP byte at max PP, keeping the PP Up bits of `ppByte` |
| `func_80063270(type)` | type name string; ids 0–9 Normal to Steel (6 is the unused Bird), 20–27 Fire to Dark |
| `func_8006456C(dvs)` | 1 if shiny: `(dvs & 0x2FFF) == 0x2AAA` |
| `func_80064474(species, dvs)` | gender: 0 none, 1 male, 2 female, from the species' ratio and `(AtkDV << 4) \| SpdDV` |
| `func_80064520(dvs)` | Unown's letter, 1–26 |
| `func_8003F954(dvs)` | `dvs % 9`, the variant of Smeargle's icon |
| `func_80064728(mon)` | picture index: the species, or Unown's letter form, an egg, a surfing Pikachu |
| `func_8004D878(dst, 0, mon)` | render a record's list icon into `dst` (shiny palette and nickname tint included) |
| `func_80042F94(model, mon)` | load the 3D model for a record |
| `func_816087C8(mon)` | gender symbol as a string, empty when genderless (fragment 11) |
| `func_800226C0(id)` | play a sound: 1 cursor, 2 confirm, 3 cancel, 5 error |
| `func_80051830(mon, saved)` / `func_80051864` | unpack / pack a registered-team entry |

After editing a record the sequence is: set experience with `func_80061B88` if the level
changed, call `func_800619E8`, then `func_80061F44`.

**Registered teams** keep the first 0x24 bytes of each record plus names, and stats are
recomputed on load (`func_80051830`). They do not store a rental index, so edits persist.

Rental entry byte 0x08 holds PP-Up bits, two per move.

DVs are packed `(Atk << 12) | (Def << 8) | (Spd << 4) | Spc`. Rentals can be shiny:
`func_8006456C` looks only at the DVs, and the icon, model and battle code all call it
(seen in the picker and in battle). The game has no helper for Hidden Power outside
the battle code, so the editor works out its type and power itself (`Edit_MoveType`,
`Edit_MovePower`). Nicknames tint a Pokémon (`func_8003F5AC`, from the name, OT name and
ID), but DVs play no part in that.

## Fragment map

`D_800CC630`: 240 entries of `{base, size}`, indexed by fragment ID. `Memmap_GetFragmentVaddr`
translates any address in `0x81000000–0x90000000` through it. ID 0x40 (vram `0x85000000`)
is unused by all 88 stock fragments. **[C]**

## Emulator harness

`tools/mod/emu.sh` drives BizHawk through `mod/lua/remote.lua` (press, wait, shot, save,
load, read, find, write, eval). BizHawk lives in `.emu/BizHawk`; output in `.emu/remote`.

- Use the **Ares64** core (`"N64": "Ares64"` in `config.ini`). The default Mupen64Plus core
  runs the game but renders black.
- Memory-write callbacks register but never fire on Ares64, so there are no breakpoints;
  use `find` and static reading instead.
- With no audio device (a locked or remote session) BizHawk stops at an "Initialization
  Error" box about the sound device before the Lua script runs, and `emu.sh start` times
  out. Dismiss the box and the script starts.
- Path to the picker: Start, Start, A, A (map); D-pad Right, Up, A (Free Battle); A, A, A
  (1P vs COM, Normal); A (Anything Goes); A (stage); Right, Right, A (Rental Only).
- `tools/mod/emu.sh script mod/lua/goto_rental.txt` replays that path from `whitecity`.
- A savestate carries the cartridge's save data with it, so to test saving, reset with
  `eval client.reboot_core()` and walk in from the title screen instead of loading one.
- Savestates: `whitecity`, `fb_rules`, `fb_entry`, `fb_rental` (stock ROM). A state taken
  with fragment 14 loaded contains that build's mod code, so after rebuilding start from
  `whitecity`, which predates the entry screen.
- To reach a battle from the picker: Yes, Start, OK; pick the COM's entry the same way;
  A through the intro; on the "All ready!" screen press the button shown on each of your
  Pokémon, then A. In battle, A opens BATTLE and holding R lists the moves.

## Drawing helpers (main segment, used by fragment 24)

Signatures inferred from call sites; names are ours. **[I]**

| Address | Use |
|---|---|
| `func_800498C4()` | begin text drawing |
| `func_800496A4(font, 0)` | select font |
| `func_8004972C(r, g, b, a)` | text colour |
| `func_800495F8(x, y, flag, str)` | draw string |
| `func_800499EC()` | end text drawing |
| `func_8004C874(bank, index)` | look up a string |
| `func_8004C990(bank, index)` | look up an image/asset |
| `func_8004D19C(x, y, image, 0, 0)` | draw image |
| `func_8004B35C(x, y, w, h, tex)` | draw textured rect |

Already named in the fork: `Ui_DrawBorderedPanel`, `Ui_DrawGradientPanel`,
`Input_GetRepeatedDPad`, `Cont_StartReadInputs`, `WidgetTree_OpenMessagePanel`.

## Move legality table

`tools/mod/gen_legal_moves.py` writes `mod/data/legal_moves.inc.c`:
`sLegalMoves[252][32]`, row = national dex number, bit = move id (8 KB).

- Rule: legal if the species or an earlier stage learns it in Gen 1–2 by level-up, TM/HM,
  tutor or egg. Event-only moves are out (`--include-events` flips that).
- Sources: Pokémon Showdown's Gen 2 learnsets, plus the Gold and Crystal level-up tables
  from the pret disassemblies. The two agree on level-up moves for all 251 species except
  Porygon's Conversion 2 and Porygon2's Tackle, which Showdown lacks; `--report` lists this.
- Egg moves come from Showdown only: Gold's table still lists moves with no possible
  father (Charm, Lovely Kiss, Staryu's set), which Showdown correctly leaves out.
- Check against the game: all 3,248 moves on the four stock rental tables pass, except
  Prime Cup Psyduck's Amnesia, an event move the developers gave their own rental.

Judgment calls, easy to revisit:

- In-game gift moves count as events and are excluded (Crystal's ExtremeSpeed Dratini,
  Odd Egg Dizzy Punch), because Showdown records them as event data.
- Pikachu's Surf is allowed: Showdown classes the Stadium 1 reward as a tutor move.
- Smeargle gets every move except Struggle, Explosion and Selfdestruct.
- Not enforced: move combinations that cannot coexist, and level requirements
  (the stock rentals ignore those too).

Tests: `python3 -m unittest discover -s mod/tests` (22 tests).

## Open questions (milestone M1)

Answered: the rental expander (`func_80071E48`), what registered teams store (full
data), the fragment map (240 entries, ID 0x40 free), the ENTER menu's handlers and that
they are shared by every mode, that an edited record reaches battle, and that a
registered edited team loads back unchanged after a reset. Remaining:

1. Free main-pool RAM while the picker is open (`main_pool_get_available`), especially on
   a 4 MB console.
2. Where cup level rules are stored (`D_82B0865C` and the rule flag word are leads).
3. Whether two players can have the picker open at once; the editor keeps one state.
4. How the existing ITEM picker scrolls, in case its widget suits the stat editor.
