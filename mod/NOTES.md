# Rental editor — working notes

Reverse-engineering notes for the rental editor mod. Addresses are for the US ROM
(sha1 `d8343e69a7dc63b869cf6361d87cde64444281d3`). Each fact is tagged:
**[C]** confirmed in source, **[I]** inferred and still to be verified at runtime.

Base: `michiiik/pokestadiumgs` at `e82d7f7` (branch `rental-editor`). Rebased there on
2026-10-11 from `e06da865`, 155 commits of decompilation later; see "Moving to a newer
base" under "Tests".
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
- **M6 in part.** `wsl_build.sh mod` also writes the release patch,
  `build/stadium2-rental-editor-us.bps` (about 84 KB), made from the original ROM by
  `tools/mod/bps.py`; applying it gives back the modified ROM exactly.
  [README.md](README.md) is the user's guide and holds the checklist for real hardware.
  - Checked: player 2 gets EDIT in a 1P vs 2P Free Battle and drives the editor with
    controller 2, while controller 1 does nothing.
  - Checked on a build that reports 4 MB of RAM (see "Memory"): editing, the shiny model
    reload and a battle all work.
  - Checked under Poké Cup rules in Free Battle: the level stops at 50 and 55.
- **Nicknames.** The name on the editor's title row is a field, reached with Up from the
  top row of any column. A opens a keyboard in the same window, laid out like the Game
  Boy's: four rows of nine keys on an upper and a lower page, over `lower`/`UPPER`,
  `DEL` and `END`. B deletes (and backs out when nothing is left), L or R switch page,
  Start jumps to `END`. Ten characters at most; `END` on an empty name restores the
  species name. See "Names".
  - Checked: `Z[×]PK♀` typed across both pages reached the record as
    `5A 5B D7 5D BC BE`, showed in the stock panel, the party box and in battle, and came
    back identical from a registered team after a console reset.
  - Checked: the tenth character moves the cursor to `END` and an eleventh is refused;
    the cursor wraps at all four edges and across the wide keys; B on an empty name
    leaves the old name; renaming tints the model and restoring the species name
    removes the tint.
  - Checked: player 2 types with controller 2 while controller 1's A, B, Start and D-pad
    do nothing; the keyboard works on the 4 MB test build.
- **Held items** stay with the stock ITEM entry, which already handles rentals, but its
  list now offers every item the game classes as worth holding (42) where the stock
  screen offers six berries plus whatever a Game Pak owns. See "Item list".
  - Checked: the list holds "No item" and the 42 in the game's order; Leftovers, eight
    rows down, was chosen for Abra and is in the party record. Names and descriptions
    draw, and the list scrolls, as it does in the stock game for a Game Pak's items.
- **Happiness** is a field beside the level (`LV 100  HAPPINESS 128`), 0 to 255 in
  steps of 1 or 25. It is the record's byte `0x1C`, and all it does in this game is set
  the power of Return and Frustration; see "Pokémon helpers". On the field the title row
  shows both powers in place of the usual traits, and the move list shows them too.
  - Checked: both ends, both step sizes, and nothing else in the record changing; an
    Abra set to 0 keeps it in the party, in battle and in a registered team after a
    reset.
- **The stock cursors.** The editor borrows what the game's own lists and menus draw:
  the brackets that breathe around the chosen entry mark the field the cursor is on
  (gold, and green while a number is grabbed), and the move list has the scroll bar
  down its left edge and the pointing hand of the ENTER menu. See "UI library pieces".
  - Checked: the brackets around a move, the name, a DV and a Stat Exp value, clear of
    the text at both ends of their cycle; the bar's knob at the top, part way and at the
    bottom of Abra's 51 moves, and gliding there after a page.
- **Trainer picture, name and title.** The menu a chosen team gets (OK / OK to Register
  / ...) has one more entry, **Change Trainer**, for a human player's team. Its window
  has three rows: the picture, stepping round the game's 67 trainers and the game's own
  choice, with C Left and C Right going round a trainer's faces from any row; the name,
  typed on the editor's keyboard, up to seven characters;
  and the title, stepping round the forty the game has. A keeps all three for that
  controller port until power off. They are then that player's where the two sides are
  set against each other, on the order screen (picture and name; it shows no title), and
  on the result after the battle. See "Popup menus", "Trainer pictures" and "Trainer
  names and titles".
  - Checked: the entry and the window; stepping round the pictures both ways, each
    byte for byte the ROM's; the rows and the titles going round; B keeping everything
    as it was; picture, name and title on the versus card, the order screen and the
    result; an emptied name giving 1P back; a remembered name given to the team on the
    next visit; the COM's team offering no such entry and the COM keeping its picture,
    name and title; player 2 choosing with controller 2 while controller 1 does nothing
    in the window or on the keyboard, and only side 2 changing; everything gone after a
    power cycle; the 4 MB build.
  - Checked for the faces: all 158 pictures in the window, each byte for byte the
    ROM's, round the whole ring and round every trainer's own; C buttons doing nothing
    on the game's own choice or a trainer with one picture, and working from the name
    and the title; a second face of the last trainer, number 156, kept, shown again by
    the window, and on the versus card, the order screen and the result; player 2's C
    buttons, with controller 1's ignored; the 4 MB build as far as the order screen.
  - A choice is one picture and stays that one whoever wins. In a battle against the COM
    the game shows no picture for the player, so there is nothing to change there.
  - Only tried in Free Battle. The pictures and titles are decided in code every mode
    shares; the name is not (see "Trainer names and titles").
  - After the keyboard the window is still on the name, where A types again: keeping
    takes a step up or down first. The hint line under the window says which A it is.
- **Editing one of the team.** A rental already entered is edited where it is, in the
  team's box, so nothing has to be taken off the team and chosen again. Two ways in, both
  from the menu a chosen team gets: the stock **Reselect some POKéMON**, whose EXCHANGE
  menu (Yes / No) has **EDIT** as a third row; and a new entry, **Edit POKéMON**, which
  is answered to the game as Reselect some but opens the editor at once on whichever of
  the team A is pressed on, and closes back to the team's box. No new hook: the EXCHANGE
  menu is the ENTER menu's code in another mode, and a place in the team's box is a cell
  like the list's. See "The team's box".
  - Checked: EDIT under Yes / No, the panel's record being the team's own; B back on No,
    then No and B back to the menu; Edit POKéMON straight to the editor and B straight
    back, twice over, and Reselect some still giving its menu afterwards; edits made
    before entering kept, added to on the team, and carried into a battle; the second of
    two edited and the first untouched; a rename's tint reaching the icon in the team's
    box, and the box repainted when the editor closes; the question over the box reading
    "Edit which POKéMON?"; the COM's team; player 2 with controller 2 while controller 1
    does nothing; the 4 MB build.
  - Checked under Poké Cup rules, with six entered: the level of one of the team goes
    from 50 to 55 and no further; with four at 55 a fifth is refused at every level above
    50 and the team comes back to its menu whole; with one of the four back at 50 it is
    allowed.
  - Not tried: a team with a Game Pak's Pokémon on it, where Edit POKéMON should sound
    the error and stay in the box.
- **Move clauses, and a rule set of the mod's own.** A rule set can keep moves out,
  by three clauses: Double Team and Minimize; Fissure, Guillotine and Horn Drill;
  Baton Pass together with Mean Look or Spider Web. Free Battle has **OU Rules**,
  which is Anything Goes without Mewtwo, Mew, Lugia, Ho-Oh and Celebi and with all
  three: on the list its sixth rule set, "Edit Rules", opens, after the player's
  own. RULE EDIT, under OPTIONS, has a row for each clause on a rule set's page, and
  "Check Rules" a line for them. Under such rules the editor does not offer a move
  they keep out, a Pokémon that knows one has "Yes" greyed out on its ENTER menu and
  the move greyed out on its panel, and a registered team with one on it has its OK
  greyed out. See "Rule sets".
  - Checked: the rule set on the list, its record, its nine lines in the viewer and
    what is behind the last; the entry screen under it, with the session still on
    Anything Goes; Diglett refused for Fissure, the cursor kept off "Yes" and ITEM
    doing nothing, the list of moves without Fissure and Double Team, and Diglett
    entered once Fissure is gone; Ariados offered no Baton Pass beside Spider Web
    and no Spider Web beside Baton Pass, and refused with both; a team of one into a
    battle; a team registered under Anything Goes with Fissure on it refused under
    OU Rules and chosen under Anything Goes; Anything Goes refusing nothing, with
    its viewer as it was; a rule set made in RULE EDIT with two clauses, saved, and
    after a power cycle on Free Battle's list with them, the viewer naming the two;
    the 4 MB build through all of it.
  - Not tried: a Game Pak's Pokémon, which is all a rule set of the player's own
    takes, and the only way to a registered team with one of the five on it (no
    rental is one); a second player; anything but Free Battle.
- **Nothing to unlock in a Free Battle.** Its list of stages has all 30 on any save
  file, where the game lists a stage once a battle has been met there, and Mewtwo,
  Mew, Lugia, Ho-Oh and Celebi are for rent under Anything Goes and Prime Cup rules,
  whose table had every Pokémon but them. The save file is not written to. See "What a
  save unlocks, and the five that could not be rented".
  - Checked on an empty save: the 30 stages in the list's state and on screen, to
    SILVER CAVE at 29/30; the 251 in the picker's table, the game's 246 records as
    they were; each of the five opened from where the alphabet puts it, with its icon
    and its stats by the formula; Mewtwo in the editor, with its own list of moves,
    and entered; Lugia in a battle with its four moves and its model; a team
    registered with Mewtwo on it refused under OU Rules and chosen under Anything
    Goes; the list under OU Rules and under Poké Cup rules the game's own table,
    record for record; the 4 MB build with the 251 and Lugia opened, the pool's free
    count not moving.
  - Not tried: the Prime Cup's rules in Free Battle (the same table and the same code
    as Anything Goes, by another rule set); a second player; a battle on any of the
    24 stages.
- An earlier build has been run on a real Nintendo 64 (reported 2026-10-12; which build,
  the cart and whether an Expansion Pak was fitted are not recorded here). So has the
  build released as v0.4.0, which has the editor on one of the team and is the first
  with the trainer pictures' second directory (reported 2026-10-13; what was tried, the
  cart and the Expansion Pak are not recorded here either). Nothing has been run on standalone ares;
  BizHawk's Ares64 core is the same emulation core.
- Known gaps: an edit lives in the list cell, so scrolling the rental far away and back
  before entering it loses the edit. An edit made on the team lives in the team's cell
  only: exchanged away and chosen again, the Pokémon is the list's copy. The stock detail
  panel and the battle menu label Hidden Power as Normal, as they do in the unmodified
  game.

## Building

The build runs in WSL (Ubuntu). From the repo root inside WSL:

    python3 tools/mod/check_rom.py <path-to-rom>   # verify + install baserom
    tools/mod/wsl_build.sh init                    # first time
    tools/mod/wsl_build.sh                         # stock ROM, must match the original
    tools/mod/wsl_build.sh mod                     # build/pokestadiumgs-us-mod.z64 and the .bps patch
    tools/mod/wsl_build.sh pull-asm                # copy asm/ back for reading

Then the tests; see "Tests" below.

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
- **Other screens.** The mod is only in memory where something loads it, and it has to
  be loaded after the stock fragment it hooks: the loader rebases the addresses of
  whatever fragments are in memory at the time and leaves the rest as linked, so a
  moved function's own references would be wrong in a copy loaded before its fragment
  was. Two ways, by what the screen needs:
  - a `boot` hook of its own, for a screen with `jump` or `detour` hooks, which need
    the mod found through the fragment map for as long as the screen is up: fragment 82,
    the rule editor, has one (`func_82D0034C`, which reads the saved rule sets as it
    starts);
  - a `call` thunk, 32 instructions, for a screen that needs the mod now and then:
    it keeps the fragment map's entry for the mod, loads a copy, calls its slot as a
    subroutine and puts the entry back. Fragments 6 and 83 are hooked this way. The
    copy stays in the screen's pool, found by nothing, until the pool is popped. The
    block's free callback (`func_800046C0`) clears a fragment's map entry only if the
    entry still points at that block, so a copy the entry was put back from frees
    without touching it: a `call` is safe inside a screen that has the mod booted
    (the viewer under the rule editor, if it comes up there). Each call is one more
    copy, 57 KB, so it is not for anything that runs every frame. Like a detour, a
    call leaves the rest of the stock function in place, so it can have a jump table
    (`func_8310065C` has); the thunk must not split an address the loader relocates
    in two halves, and must end before the first place the table leads to.
- **A copy that nothing finds still holds its data.** `Mod_RuleViewerLines` leaves the
  viewer a pointer into the copy it ran in, which is good until the viewer's pool goes.
- Only asm functions can be hooked so far (the tool takes their size and body from
  `asm/us/nonmatchings`). Hooking a decompiled function needs its body from elsewhere.
- `mod/asm_patches.txt` changes single instructions in a moved function, by address.
  That is also how a call inside a stock function is pointed at the mod: move the
  function and patch its `jal`.
- A function with a jump table cannot simply be moved: the table is stock data and still
  holds addresses inside the stock function, so the moved copy's switch lands back in
  the stock body. The `detour` hook kind is for that: only the thunk's five
  instructions are overwritten and only their relocation entries dropped, and the rest
  of the stock function stays as it was, to be run from wherever the table sends it.
- **Stock code the mod is not in memory for** is changed in place instead:
  `mod/stock_patches.txt`, same format as `asm_patches.txt`, for any fragment. The build
  assembles each such function with its changes (`build/mod/patched.s`, never linked)
  and `modtool.py inject` copies just the changed words into the ROM. It refuses an
  instruction that has a relocation, in the object or in the fragment's table, so a
  patch cannot name a symbol and has to leave relocated instructions (every `jal`, every
  `lui`/`addiu` pair of an address) where they are. Branches within the function and
  fixed addresses such as `0x80000358` are fine.
  - A patch has only the room of the instructions it replaces. Where that is not
    enough, instructions an earlier patch left unreached can hold the rest (`0x826103E8`
    on, in `func_826101B4`, serves `func_82601BB0`, and is now full): a branch there and back is
    relative, so it needs no relocation even between functions, as long as both are in
    the same fragment and within a branch's reach. The assembler takes `. + offset`.
  - A line that leaves an instruction as it was is an error in the tests
    (`test_every_stock_patch_changed_its_instruction`); leave such a line out.
  - The main segment can be patched as a fragment can (it has no relocation table to
    mind), and so can what a `detour` or a `call` leaves of its function past the
    thunk.
  - A function the decompilation has in C has no assembly file to put the lines into.
    Its lines are assembled each alone, so they cannot use the function's labels: a
    branch is `. + offset`. The rule sets' packers are patched this way. (One of the
    two still has a file in a tree extracted before it was decompiled; the lines are
    written to work either way.)
  - **Never work out an address from a value that may be negative.** A port of -1 added
    to `0x80000000` (as `lui $at, 0x8000` holds it, sign-extended to 64 bits) gives
    `0xFFFFFFFF7FFFFFFF`, which is not a sign-extended 32-bit address, and a load from it
    is an address error on this processor: the screen hung on a white picture. Test the
    port first and load after. BizHawk's Ares64 core faithfully hangs; an emulator
    that works in 32 bits would not have shown it.
- `modtool.py inject` refuses to build a fragment the loader could get wrong: every
  LO16 must have a HI16, the table must pass the order check, and no `lui` may serve two
  addresses inside the mod. Hence `Edit_GetState` in `mod/src/state.s`: C code reaches
  the editor's state only through that pointer. A stock fragment's data that C code
  reaches at several offsets is taken there too (`RuleViewer_GetState` and the like):
  the compiler may share a `lui` between the offsets as it would for the mod's own.
- **The mod is past 0x8000 bytes**, since the rule sets came (0xBB20 of code and data,
  0xDDB0 in memory). An address in its upper part has a lower half that counts down
  from the next 0x10000, and its relocations, as the linker leaves them, all name the
  start of the section. `fragment_relocs.py` chose a LO16's HI16 by which formed the
  address nearest that start, which for such an address is the wrong one, the `lui` of
  some lower address; the table then failed the order check. It now takes no `lui`
  that would put one of the mod's own addresses before the mod.

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
- **The asset blob is archives found through a table** at ROM `0x437620`: 19 addresses of
  four bytes, read once at boot into `D_80124D00` (`func_80035620`) and looked up by
  `func_800356CC(n)`. **[C]** 1 is the images, 2 the texts, 0xB the rosters, 0xF the
  trainer pictures. Most are a header `{flags, 0, size, count}` and a directory of
  `{offset, size, 0, 0}`, offsets from the archive's start (`BinArchive_Open`,
  `src/4420.c`); 9 and 10 are not. So an archive can be given another directory
  somewhere else by changing its four bytes in the table, which is how the trainer
  pictures get theirs.
- **Each archive is padded with `0xFF` to the next**, which starts on a multiple of
  0x1000, and seven of those gaps are over 50 KB: `0x16FB090`, `0x188A8D0`, `0x1D63410`,
  `0x1E2DE80`, `0x2222590`, `0x225A820` and, to the end of the ROM, `0x3FEDFD0`; 419,472
  bytes together, besides the mod's own hole. The mod uses `0x225A820–0x2268000`
  (55,264 bytes, of which 4,000 from `0x225B000`), which `check_rom.py` verifies too.
  **[I]** that the others are as dead: each starts where its archive's size says it
  ends, but only this one and the hole have been written to and run. The ROM is 64 MB
  already, so this padding is all the room there is for new data.

## Game flow

`Game_Thread` (`src/65820.c`) switches on the game state in `D_8009DE94`:
17 boot (fragment 15 logos, fragment 67 intro), 2 Game Pak Check / "Please Select",
3 White City map, **16 Free Battle setup and entry**, **13 the battle loop**.

- State 16 (`func_80068E14`): rule select, stage select, then the entry screen in
  **fragment 14** with shared UI fragments 11 and 18 loaded. **[C]** from the live fragment map.
- State 13 (`func_800684F0`, tags `btpc`/`btlp`) is a loop of screens. In Free Battle:
  **fragment 20** (with 81; the opponent's introduction, then both sides set against
  each other under "VS"), **fragment 12** (with 80 and 11; the order screen, "All
  ready!"), **fragment 79** (the battle), fragment 20 again in its other mode (the
  result), and round to the introduction. Fragment 24 comes first in other modes
  (`session->0x34` set); it was not loaded in a Free Battle. **[C]** from the fragment map.
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
- The list itself is an object of 0xE918 bytes, set up by `func_8130B220(list, panel,
  controller, count)`: `+0xE8EC` the detail panel it opens, `+0xE910` the controller that
  drives it, `+0xE912` its state. **[C]** in source since the rebase; not used by the mod.
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

### Item list

The ITEM entry opens a list object at `state + 0xD18` (`panel->0x5C`), in
`fragment14_FD770.c`. **[C]** in source and at runtime.

| Offset | Field |
|---|---|
| 0x08, 0x0A | cursor column (0–1) and row on screen (0–3) (s16) |
| 0x10 | item ids, up to 0x40 bytes; entry 0 is 0, "No item" |
| 0x50 | number of entries (u16) |
| 0x54 | mask of items that cannot be taken (32 bytes), given when the list is opened |
| 0x7C | first row shown (s16) |
| 0x87 | state: 0 closed, 1 open; the others are its animations |

"No item" has the top row to itself and the items follow two to a row, so the cursor is
on entry `(top + row) * 2 + column - 1`. Four rows show at a time.

- **What is offered** is a mask of 256 bits, one per item id (`func_81601980` tests a
  bit, `func_816019C0` sets one, `func_81601A38` fills the mask). `func_81300244` builds
  it in `D_81312A40` each time a player picks where their Pokémon come from: six berries
  (`func_81601A78`: PRZCureBerry, Burnt, Ice, Bitter and Mint Berry, Berry), plus the
  items found on a connected Game Pak (`func_81601B00`).
- **The list** is made from the mask by `func_81602134`, called from the list's setup,
  `func_81306B64(list, x, y, arg3, mask)`. An item is listed when its bit is set and
  `func_81601FA0(item)` gives it a group from 1 to 5, and the list runs group by group:
  1 the six berries, 2 healing (hold effect below 0x11), 3 other effects, 4 type boosts
  (hold effects 0x32–0x42), 5 the species items. Group 0 is not listed: no hold effect
  (`func_80063660`, the table at `D_80097FED`, three bytes an item), or one with no use
  in a battle (Amulet Coin, Cleanse Tag, Smoke Ball).
- **The mod** hooks `func_81306B64` and passes a mask with every bit set
  (`Mod_ItemListInit`), so the list is what a Game Pak owning every item would give: 42
  items, 43 entries. The game's own mask is left as it was.
- **What cannot be taken** is separate and unchanged: a second mask, kept at
  `panel->0x3C`. `func_8130EA8C` puts the species items of other species in it
  (`func_81601D24`: Light Ball for Pikachu, Lucky Punch for Chansey, Stick for
  Farfetch'd, Metal Powder for Ditto, Thick Club for Cubone and Marowak), and
  `func_81304788(party, mask, slot)` builds one of the items the rest of the party
  holds, unless the rules allow two of an item (`func_80071230`). **[I]** that the two
  end up in the same mask. `func_81306C18(list, item, mask, …)` opens the list with it,
  on the Pokémon's item or else the first one free.
- Choosing an item enters the Pokémon at once (`func_8130F0FC`: the item goes to
  `panel->0x39`, the cursor to Yes, and the panel closes).
- The line under the list is `func_816020BC(item)`, text bank 9: the item's description.

### Popup menus

The lists of choices that pop up over the screen, the menu a chosen team gets on Start
among them, are one widget (`fragment14_109280.c`), at `state + 0x74`. **[C]** in source
and at runtime. See `Menu`, `MenuDef` and `MenuEntry` in `mod/include/game.h`.

- A menu is drawn from a **definition** of 0x24 bytes: `+0x08` the point the box is
  placed against and `+0x0C` how (x centred on it, y from it down), `+0x10` margins
  (top, bottom, left, right), `+0x14` font, `+0x16` row spacing, `+0x18` the result for
  B, `+0x1C` entry count, `+0x1E` text bank, `+0x20` the entries. An entry is 8 bytes:
  `+0x00` text id, `+0x04` result, `+0x06` nonzero to centre it.
- The screen calls `func_81311C70(menu, definition, controller, -1)` every frame it
  wants a menu up. That opens it if it is not (`func_81311B98` → `func_813110F0`, which
  measures every entry's text for the box's width), returns 0 while it is open, and
  once an entry is chosen or B pressed returns that result and closes it. Menu:
  `+0x00` its definition, `+0x04` how far open (0 to 16), `+0x10` the box (x, y, w, h),
  `+0x18` status (0 closed, 1 opening, 2 open, 3 closing, 4 done), `+0x19` cursor,
  `+0x1A` controller.
- `func_81311650(menu, ctx)` draws it and `func_813114B8(menu, row)` one entry: its text
  from the bank, yellow under the cursor, at `x + left margin`, `y + top margin +
  spacing * row`.
- **The team menu** is asked for by `func_81303648(party)`, with the definition
  `func_813035A0(party)` picks from six (`D_81311E5C` on: five, four or three entries
  from OK, OK to Register, Reselect some, Reselect all and Change Item, text bank 0xF
  0x1A–0x1E, results 0–6). It acts on the result through a jump table and ignores any
  other value.
- **The mod's entries** are added by handing the menu a copy of the definition with one
  or two more (`Trainer_ExtendMenu`): **Edit POKéMON**, result `0x7E`, when the team has
  a rental on it, and **Change Trainer**, result `0x7F`. `func_81303648` runs from the
  mod (a `detour`, for its jump table) with its call of `func_81311C70` pointed at
  `Mod_PollTeamMenu`; `Mod_DrawMenuRow` draws the entries' texts, which no bank has, and
  the stock code does the rest: box size, cursor, pointing hand. An entry's own text id
  is the first stock entry's, which is only measured. Change Trainer is not on the COM's
  team's menu: `settings + 0x900 + side` is the side's controller port, negative for the
  COM, and `state + 0x1A142` the side whose team is being chosen. The copy is made again
  when the stock definition or the set of entries changes. With seven rows the box ends
  about ten pixels above the bottom of the screen.
- **A measurement in the middle of drawing** can leave the text undrawn:
  `func_80049148` between `func_800496A4` and `func_800495BC` did, with the large font
  (0x10) of the question over the team's box. Measure first. (The editor measures as it
  draws all the time, but in the one font it draws with.)
- While the trainer window is up the menu is closed and `Mod_PollTeamMenu` answers 0,
  "still open", without asking it; the frame after the window closes, the stock code's
  next call opens the menu again. The screen still calls `func_81311650` for the closed
  menu every frame, which is where the window is drawn from (`Mod_DrawMenu`), or the
  keyboard while a name is typed. The two are different regions, being in different
  places on the screen (see "Redrawing").

### The team's box

The team being chosen is an object at `state + 0x15370` (`fragment14_FAD40.c`; the same
one for each side in turn, the COM's included). **[C]** at runtime for the states the
tests pass through, **[I]** from the assembly for the rest.

- `+0x08` the cursor's place (s8), `+0x0A` the controller, `+0x20 + n * 0xCE8` its six
  cells, `+0x4DA0` the picker's state, `+0x4DAC` set to have the box repainted, `+0x4DBD`
  what it is doing. The box is three places wide and two high, and the cursor does not
  wrap.
- `func_81303EF4` runs it each frame, by a jump table on `+0x4DBD`:

  | State | Handler | |
  |---|---|---|
  | 2, 3 | `func_813032D0`, `func_81303364` | opening, closing |
  | 4 | `func_81303648` | the team's menu is up |
  | 0xC | `func_813032B0` | handing the cursor to the list |
  | 0xD | none | the list has it; the place being filled reads "Sixth POKéMON" and the like |
  | 0x11 | `func_81303A88` | "Reselect some": the cursor is in the box, under "Exchange which POKéMON?" (text 0x1F). A on a filled place → 9; B → 4, or 0xC with the cursor on the last place when the team is over the level total |
  | 9 | `func_81303D60` | opens the detail panel on the place's cell, mode 1 → 0xE |
  | 0xE | `func_813033DC` | waits for the panel: Yes → 0xD, to choose another for that place; No → 0x11 |
  | 0x12, 0xA | `func_813037F0`, `func_813038D0` | Change Item: the item list and the panel in mode 3, place by place |
  | 7, 8 | `func_81303E20`, `func_81303EA8` | the message that the level total is too high, then 0x11 |
  | 0x10, 5, 6 | `func_81303CA0`, `func_81303BF4`, `func_81303D04` | OK with a check, and its messages |

- **What the list asks of it**: A on a Pokémon ends in `func_81304444(party, cell, item)`,
  which copies the cell to the cursor's place and, with the team full, goes to 4 (or 7);
  Start is `func_813042E4`, which goes to 4 only if the rules' flag word has bit 31 set
  (Anything Goes does; the Poké Cup, `0x0FFF0000`, does not, so its menu waits for six);
  B is `func_8130437C`, which takes the last Pokémon off again, or goes to 0x11 if the
  cursor's place is filled.
- **The level total** (`rules + 0x38`; 155 for the Poké Cup) is held against
  `func_8160A9F0(party)`: the lowest that any three of the team's levels come to, 600
  with fewer than three (`func_81303A38`). A team over it is not let back to its menu.
  B in the box then sends the cursor to the list with the last place open again, its
  Pokémon gone. The editor would walk a team into that with a level, so for one of the
  team `Edit_SetLevel` stops at the highest level that keeps the team within the total.
- **The mod's editor on one of the team** needs nothing of all this changed. The panel
  in mode 1 is the ENTER menu's code with EXCHANGE for a title and no ITEM row, and its
  record is the place's cell, so `Edit_CanEdit` takes mode 1 as well and the icon in the
  box is reloaded as the list's is. Leaving the editor puts the menu's cursor on No.
- **Edit POKéMON** is `Mod_PollTeamMenu` answering 4, Reselect some, with
  `EditState.pending` set. `Mod_EnterMenuInput` then opens the editor on the first panel
  that comes up in mode 1 (`EditState.direct`), and B in the editor closes the panel as
  B on its menu would (`Edit_ClosePanel`: cursor on No, state 3, `+0x2C` to 1.0), which
  0xE takes for No. `pending` is cleared when the team's menu is asked again or a panel
  comes up in any other mode. While it is set, `Mod_DrawMenuRow` draws the question over
  the box as "Edit which POKéMON?", in the middle of a box measured for the stock one.

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
| `func_81607440(x, y, w, h, position, …)` | vertical scroll bar: the trough (`func_816054D8`) and a 16 x 20 knob whose middle runs from `y + 13` to `y + h - 13` as `position` goes from 0 to 1. Clips to itself and leaves the clip at the full screen. The stock lists pass two more arguments, whether there is more above and below (`func_8160762C`), which it never reads |
| `func_81608918(x, y, &timer)` | the pointing hand (`func_8004AF18`, main segment), sliding 6 pixels right and back every 24 frames; `timer` is an `f32` the caller keeps. About 32 pixels wide, drawn at the text's own y |
| `func_8004B09C(x, y, w, h, &phase, r, g, b, animate)` | main segment: four corner brackets around a rectangle, moving in and out by 2 pixels on a sine. A corner is 16 x 15, so they stay apart from 30 pixels of height up. `phase` is a `u16` that each call moves on by 0x2000 when `animate` is set. `func_8004B314(x, y, w, h)` is the same in the stock gold (`F0 D4 68`) on a phase shared by every caller |

The stock ITEM list (`func_81305C54`) is where these were read from: the bar at the
window's inside left edge, 19 wide and as high as the inside; names at `x + 0x26 +
172 * column`, `y + 0x12 + 28 * row`; and the brackets 157 x 36, starting 5 pixels up and
left of the name. The editor's rows are 22 apart, too close for brackets that tall to miss
the next row's text, so its brackets stand a corner's width out to either side of a field
instead. The knob in the stock list eases towards its place, and the editor's does too
(`EditState.scroll`, halving the distance each frame).

The font has no `<` or `>` glyphs. The ENTER box's inside is `x + 0x198`, `y + 9`,
129 x 128, colour `#3333F8`; the editor paints its key hints there.

### Button pictures and key hints

The game never lists a screen's controls, and never explains A or the Control Pad. What
it does, and so what the mod does:

- **A button's picture beside the thing it acts on.** On the entry screen: L and R at the
  ends of the list's tabs, START beside "3 POKéMON", a C direction beside each move.
- **One line in the box it belongs to, the picture and then "to *verb*".** "to check TM"
  and "to quit" in the ENTER menu and ITEM list (text bank 0xF, 7 and 8); "to return"
  and "to go next" in the Academy (bank 0x38). In `func_8130DA04` the picture is at
  `x + 0xE` and the text at `x + 0x27` of the box, the picture 4 higher than the text.
- **One line of them along the bottom**: My Room (fragment 13, `func_8240227C`) has the
  Control Pad with "MOVE CAMERA", A with "DECORATION" and B with "Quit".
- **Nothing.** The game's own keyboard (fragment 36: Name Box, Write Mail, Name Rule)
  acts on B, START and the C buttons and says so nowhere.

| Bank | Images | Loaded on the entry screen |
|---|---|---|
| `0x33` | 24 x 24, in colour: 0 A, 1 B, 2 C, 3 C down, 4 C left, 5 C right, 6 C up, 7 START | yes (`func_81602DD8`) |
| `0x34` | 40 x 32, grey: 0 L, 1 R; the button is 36 x 26 and the rest its shadow. `func_8160710C(x, y)` draws L and `func_816071AC` R, each setting the render mode it needs | yes |
| `0x94` | 20 x 20: the Control Pad | no (My Room) |
| `0x1E` | 16 x 18, to be tinted: 0 A, 1 B, 2 to 5 C down, left, right, up; 6 L and 7 R at 24 x 17; 8 not identified | no (My Room) |
| `0x31` | 24 x 20: START again, as the order screen has it | no |
| `0xEA` | 16 x 18, grey: 0 down, 1 left, 2 right, 3 up, My Room's arrows; the arrow is 11 x 15 and the rest its shadow | no, so the mod loads it (`Mod_EntrySetup`) |

A round one is drawn as the ENTER menu does: `func_8004C990(0x33, n)` for the image and
`func_8004D19C` after `gSPDisplayList(D_80094E38)`. Only the banks the screen has loaded
can be used; `func_8004C990` gives NULL for the rest, and `func_8004C8C0(bank)` loads
one into the main pool, where it stays until the screen's pool state is popped. The
entry screen takes the rest of the pool once it is set up, so the mod loads the one bank
it adds, the arrows, from its boot hook. An image with a soft edge (the shoulder buttons,
the arrows) wants `gDPSetRenderMode(0x0F0A7008, 0)` after `D_80094E38`, as
`func_8160710C` sets it.

Where the mod has them (`Edit_DrawSidebar`, `Edit_DrawKeyButtons`, `Trainer_DrawWindow`):
the EDIT box says B "to quit" with the game's own text, and L "to min", R "to max" while
a number is grabbed; the keyboard's wide keys each have the button that does the same
from anywhere, R before `lower` / `UPPER`, B before `DEL`, START before `END`; and the
trainer window has one line, A with "OK" (or "Type" on the name, where A opens the
keyboard) and B with "Quit", and before them, for a trainer with more than one picture,
C Left and C Right with "Face": nothing on screen would say so otherwise. B comes last,
as in My Room's line. What the cursor already says is left unsaid: moving, and A on
what it points at.

Left and Right going round the trainer's pictures and titles is not something a cursor
says, and the font has no arrows (`<` and `>` neither), so the window has My Room's:
one either side of whichever the cursor is on, the picture's place in the ring or the
brackets round the title. The Control Pad's picture before "Change" in the hint line,
which is My Room's own way, was tried first; it cannot say which way to press.

**The EDIT box is lower than the ENTER menu's**, having less in it. `func_8130D1FC(panel,
&rect)` works the menu's box out, and both users take it from there: `func_8130DA04` to
draw the frame and clip to it, and the panel's update (`func_8130F2C4`) to register the
region, key `panel + 1`. It goes between two rectangles of `D_81312730` by
`panel->opening` (open: `x + 0x191`, `y`, 147 x 146, or 147 x 49 for panel modes 2 and
up), and adds up to 53 to the height while the ITEM list is open (states 5 and up, eased
over `panel->0x30` from 0 to 12), which is where "to quit" goes. The mod hooks
it (`Mod_EnterMenuRect`) and scales the height to `EDIT_MENU_HEIGHT` while the editor is
open: enough for the two shoulder buttons of a grabbed number, the most the box ever
holds. Nothing has to be repainted by hand when it changes: a region whose rectangle
changed is dirty, and so is what it no longer covers.

To look at the art outside the game: the images are archive 1 of the table at ROM
`0x437620`, at ROM `0x1898000` (the texts, archive 2, are at `0x1D70000`): `+0x0C` a
count, then `{offset, size}` every 0x10 bytes. A bank is `PERS-SZP` with Yay0 data at
the offset in `+0x08`; unpacked, a count, that many offsets (low 20 bits, less 8), and
at each an 8-byte header (width, height, format, pixel size) and the pixels. On odd rows
each pair of 32-bit words is swapped.

### Rules

`*(Rules **)(D_8133197C + 0x940)` is the rule set in force: one of the game's records in
the main segment (Anything Goes is at `0x8009F5C4`), or the session's own copy of one.
See "Rule sets" for the record and for where the pointer comes from.

- **Who may be entered** is asked in three places. `func_8130456C(party, cell)` for a
  cell of the list: its species and level by the rules (`func_8007126C`), and whether
  the team has it already (the same Pokémon, or the same species unless the rules
  allow that). The list sounds the error on A where that says no. The ENTER menu
  greys out "Yes" for a held item the rules reject (`func_8130CE3C`), puts the cursor
  on its last row as it opens (`func_8130EB04`) and keeps Up from reaching "Yes"
  (`func_8130EC9C`); the panel shows the item's name in grey (`func_8130DEB8`). And
  the team as a whole has its levels' total (see "The team's box").
- **The mod's move clauses** go with the second: "Yes" greyed out, the cursor on EDIT
  for a rental (where the move can be changed) or on No, ITEM refused because choosing
  an item enters the Pokémon at once, and the move's name grey on the panel, where the
  game colours it by its type (`func_81602DA4`, in a loop that has the record plus the
  slot in `$s1` and four times the slot in `$s3`). `func_8130CE3C` is C, so its
  callers in moved functions are pointed at `Mod_EnterYesDisabled`; the one in
  `func_8130EB04`, which is not moved, is made up for by moving the cursor.
- **A registered team is entered whole**, from the menu its list gives the one chosen
  (OK / Select again / Check: `func_8130C14C`, with the definitions at `D_81312054`;
  OK is text `0x52` and answers 3). Nothing holds it against the rules: the game keeps
  the teams of each kind of rules apart (`settings + 0x944`, from `func_8006B854`: 0
  for Anything Goes, 1 to 3 by the mode otherwise, -1 for a player's own rules, which
  have none). The mod's rule set shares Anything Goes's, so under rules with clauses
  the mod greys that OK out and refuses A on it (`Mod_MenuInput`, in place of the
  popup's input `func_81311894`) for a team with a Pokémon on it that the rules keep
  out or that breaks a clause. The team the cursor is on is `func_8130B1F4(list)`,
  the list being the object at `state + 0xD18`, laid out as the team being chosen is.
  "Check" shows its Pokémon on the panel, the move in grey.
- **The list of registered teams heads itself** "Registered POKéMON / " and the rule
  set's name, looked up by the record's text (`+0x3E`) with no thought for a record
  that has none (`func_8130C570`, at `0x8130CA40`); the screen's other headings show
  the record's own name then (`func_8130015C`). The mod's `Mod_RuleName` does the same
  there.
- A rule set of the player's own gets no rentals and no registered teams:
  `func_81300E34` and `func_813010B0` give the entry screen's choices "rentals" only
  if the kind is not 0xE. Under one, with no Game Pak, the screen says "There is no
  POKéMON Game Pak to choose."

### Input

`func_8130EC9C(panel)` reads `D_800CE060[panel->0x37]` (0x28 bytes per controller):
`+0x08` held buttons, `+0x0C` newly pressed. A on cursor 2 opens the item list; A on
anything else, or B, closes the menu with result `cursor + 1`. Up/down move the cursor
within `func_8130CEAC`'s count. C buttons open the "check TM" popup for a move.

## Rule sets

### The record

0x44 bytes. **[C]** from the fourteen in the ROM and the code that reads them.

| Offset | Field |
|---|---|
| `+0x00` | name, 0x14 bytes; empty in the game's own |
| `+0x14` | who may enter: a bit per species, species 1 the top bit of the first byte |
| `+0x34` | kind (s16) |
| `+0x36`, `+0x37` | lowest and highest level |
| `+0x38` | the most three levels may come to (u16); 600 for no limit |
| `+0x3A` | background of the entry screen |
| `+0x3C` | which table of rentals (s16); -1 for none |
| `+0x3E` | the rule set's name as a text of the entry screen's bank 0xF (s16); -1 to show `+0x00` |
| `+0x40` | flags |

Flags: bit 31, Start may end a team short of six; 30, a species may be on a team
twice (`func_80071210`); 29, so may an item (`func_80071230`); 28, set only for kind
6; 27, Dragon Rage and Sonicboom work (clear only in the Little Cup: the viewer's "The
move has no effect"); 26, items may be held. Bits 25 to 16 are set in all fourteen and
read by nothing found. **Bits 15 to 0 are clear in all fourteen**, and a player's rule
set is made from nothing but bits 31 to 26. The mod's clauses are bits 0 to 2.

The sleep and freeze clause and the rule on the last Pokémon are not flags: the viewer
lists them for every rule set, and every battle has them.

`func_800718B8(kind)` finds the game's records, `D_8009F828[kind]`, for kinds 0 to 13:

| Kind | At | | Levels | Rentals | Flags |
|---|---|---|---|---|---|
| 0 | `0x8009F470` | Little Cup (86 species) | 5 | 0 | `0x07FF0000` |
| 1–4 | `0x8009F4B4` on | Challenge Cup, by ball (57 to 59 species) | 0–100 | 0 | `0x0FFF0000` |
| 5 | `0x8009F5C4` | Anything Goes | 0–100 | 1 | `0xEFFF0000` |
| 6 | `0x8009F608` | Gym Leader Castle | 0–100 | 4 | `0x1FFF0000` |
| 7–10 | `0x8009F64C` on | Poké Cup, by ball: no Mewtwo, Mew, Lugia, Ho-Oh, Celebi; total 155 | 50–55 | 3 | `0x0FFF0000` |
| 11 | `0x8009F75C` | VS Rival | 0–100 | 1 | `0x8FFF0000` |
| 12, 13 | `0x8009F7A0`, `0x8009F7E4` | Prime Cup | 0–100 | 1, 2 | `0x0FFF0000` |

Kind 14 (0xE) is a rule set of the player's own, which has no record here.

### Kinds and the session

A rule set is chosen as a record, by value, but the session keeps only its kind unless
the kind is 0xE (`func_80068B78`, with what Free Battle's set-up filled in):

- any other kind: `func_8006A444(kind)` puts the kind at `session + 6` and clears
  `session + 0x3C`, 0x44 bytes. Whoever wants the rules looks the game's record up
  again by kind;
- kind 0xE: `func_8006A4AC(record)` copies the record to `session + 0x3C`.

So `func_8006B928` gives the entry screen `settings + 0x940` as one or the other, and
`func_8006C664` the battle its `+0x9D4` likewise.

**The kind decides much besides.** `func_80068AB0(kind)` makes the session's mode of
it: `0x0220` for Anything Goes, `0x0210` for a player's own rules, `0x0200` to `0x0203`
for the cups. Battle music goes by kind (`func_8006A51C`), the battle asks whether the
kind is 5 before it has two players on a side as a tag team, the entry screen's
background and its rentals are by kind (above), and the viewer's lines are mostly by
kind. A player's own rules are, in all of that, a cup: six entered, three of them
chosen to fight, no rentals, no registered teams.

### OU Rules

So the mod's rule set is not of the player's kind, though it is on their list. It is a
record of kind 5 (`mod/data/rule_ou.inc.c`): Anything Goes's record with the Poké
Cup's species, the clauses' bits, a name, and -1 for its text. To the session it is
Anything Goes, and the session forgets the rest. What decides who may enter is all on
the entry screen, so that is where the record is put back:

- `gChosenRules` (`0x80000330`, a byte of `osAppNMIBuffer`) is 1 while Free Battle's
  last rule select ended on the mod's rule set: `Mod_RuleSelectDone`, in place of
  `func_8310065C`, sets it by the record the screen filled in (kind 5, with clauses),
  and `Mod_RuleSelectSetup` clears it as the next one starts.
- `Rules_UseChosen`, as the entry screen starts (`Mod_EntrySetup`): if the byte is set,
  the mode is a Free Battle's and the rules given are Anything Goes's, the record is
  copied to `session + 0x3C`, which Anything Goes leaves empty, and `settings + 0x940`
  pointed there. Not at the mod's own copy: the settings outlast the entry screen.
- A battle is one of Anything Goes: its rules pointer is the game's record, which
  differs from the mod's in nothing a battle reads.

It allows a species and an item twice, as Anything Goes does.

### Free Battle's rule select (fragment 6, vram 0x83100000)

One screen for the players, the rule set and the stage. Its state is `D_831039B0`,
0x2F4 bytes; `+0x38` is what it fills in, `func_80068CBC`'s 0x5C bytes.

- **Six rule sets**, in a panel they fill: Anything Goes, Prime Cup, Poké Cup, Little
  Cup, Challenge Cup (which asks for a ball) and "Edit Rules". `+0x3E` is the row, 1 to
  6, and `D_831038FF` has the kinds of the first five rows for "Check Rules". A seventh
  row has nowhere to go.
- **"Edit Rules" opens the player's own**: up to eight records at `+0xCC`, their count
  at `+0x2EC`, read from the save file by `func_83100584` as the screen is set up
  (`func_83101C80`). `func_83101804` draws their names in a list of eight places, and
  A on a place past the count sounds the error. `+0x3F` is the place, from 1.
- **The mod's rule set is one more record there**, put after the player's by
  `Mod_RuleSelectSetup` if they have fewer than eight.
- **Ending** (`func_8310065C(state, cancelled)`, from a stage chosen or from B at the
  first step): the record goes to `+0x10` of what is filled in, by the row: looked up
  by kind for the first five, copied from the list for the sixth. So a record on the
  list goes on as it is, whatever its kind.
- R, "Check Rules", copies the record the cursor is on to `+0x68` and runs fragment 83
  on the copy, with `0x200` for where it was called from.

In the Free Battle path fragment 6 is at `0x8015AF10`, and the pool has `0x4BA660`
bytes free at the rule sets with 8 MB.

### The rule viewer (fragment 83, vram 0x82C00000)

`fragment83_main(where, rules)`. Its state is `D_82C04C38`: `+3` the number of lines,
`+0x14` and `+0x18` the two arguments, `+0x1C` the heading, and from `+0x50` the lines,
0x1CC bytes each: `+0x00` 0 for a line with something behind it or 1 for the one that
opens the species, `+0x04` the title (0x50), `+0x54` what is behind it (0x168).

- `func_82C04350` makes the lines: fifteen functions in turn, each writing the next
  line and answering whether it did, from text bank 0x15 by the rule set's kind and
  flags and by `where`.
- **There is room for ten**, in the state and on the screen, and a player's rule set
  in Free Battle can have ten. So the clauses are one line, "Moves that cannot be
  known", with a sentence behind it for each clause the rule set has, and a rule set
  with ten lines already does not get it. `Mod_RuleViewerLines`, in place of
  `func_82C04350`, adds it.
- **The heading** is "Check rule " and a name: by kind a text of bank 0x13, or for
  kind 0xE the record's own name (`func_82C0458C`, which runs after the lines). For a
  record with a name and another kind, the mod's, `Mod_RuleViewerLines` gives the
  viewer a copy that says it is 0xE. Hooking `func_82C0458C` itself would not do: two
  of the places its jump table leads to are under where a `call` thunk would go.
- The move names in the mod's sentences are the game's (text bank 6, in the moves'
  order), which the viewer does not load; `mod/tests/test_clauses.py` holds them
  against the ROM.

### The rule editor (fragment 82, vram 0x82D00000)

RULE EDIT, under OPTIONS (game state 11, fragment 22) on "Please Select". **[C]** for
what the mod uses.

- The player's rule sets are at `D_82D2393C`, their count at `D_82D23938`, read by
  `func_82D0034C` as the editor starts; `D_82D23D84` is what the editor is doing, and
  `D_82D23D88` the buttons pressed.
- One widget (number 8, state `D_82D23830`) is the list of them and the page for one:
  `+0` what it shows (1 to 3 the list; 4 the page; 5 the keyboard; 6 the page with the
  species open over it; 7 and 8 the page dimmed, a level being set), `+1` the cursor.
  The rule set on the page is `D_82D238F0`, `+0xC0` from there. `func_82D03CC0` draws
  all of it and `func_82D00BB4` is the page's input.
- **The page** is seven rows by number: name, who qualifies, level, level total, "Use
  items?", "Hold identical items?" (skipped while items are not used), OK. A question
  at `x + 0x3A` with its answer ending at `x + 0x1DA`, 30 apart from `y + 0x20` with a
  row left out for "(No restrictions)", and OK at `y + 0x10A`. `func_82D0087C` is A on
  a row, by a jump table of the seven.
- **The clauses are rows 6 to 8, and OK row 9** (`mod/src/rule_edit.c`).
  `Mod_RuleEditInput` replaces the input: the game's cursor mover over ten rows, A on
  a clause's row flipping its bit, and OK handed to the game's code as row 6.
  `Mod_RuleEditDraw`, a detour of the drawing, adds the three rows, OK and the hand
  on any of the four. The game's own OK is given up by two instructions changed in
  place: its text looked up as 0x10, the bank's empty one, and its hand put off the
  screen.
- **The window** of the page is `D_82D07174`: (74, 113, 498, 326), among three
  rectangles the widget's window goes between. Ten rows need more, and
  `Mod_RuleEditSetup` makes it (74, 93, 498, 356): exactly as high as the window of
  species that opens over it (widget 9: 93 to 449), so that one goes on hiding it. The
  mod's rows are then 28 apart.
- A new rule set has flags `0x0C000000` (`func_82D00704`), its clauses off.
- "Make rules" asks for a place on the list first; B at the top leaves, and OPTIONS
  asks whether to save on the way out.

### Saved rule sets

A rule set of the player's own is saved as 0x48 bytes (`func_800519AC` to that form,
`func_80051890` from it; `src/517E0.c`): `+0`, `+1` the levels, `+2` their total, `+4`
to `+9` a byte for each of flags 31 to 26, `+0xB` the kind, `+0x14` the species,
`+0x34` the name. `+0xA` and `+0xC` to `+0x13` are cleared and not read.

- **The clauses go in `+0xA`**: the low byte of the flags on the way out, its low
  three bits on the way in. Both functions run with the mod nowhere near, so they are
  changed in place (`mod/stock_patches.txt`); each took a flag at a time through
  memory, and done in registers there is room for one more byte.
- A save file from before has 0 there, which is no clauses. The original game reads a
  rule set saved by the mod as one without, and saving it there loses them.

### Where the clauses are held to

`mod/src/clauses.c`, by the rule set in force on the entry screen
(`Clauses_Of(Rules_InForce())`): `Clauses_MoveRefused(rules, mon, move, slot)` is
whether a Pokémon may know a move in a slot beside its other moves, and
`Clauses_Broken` whether it knows any it may not.

- The editor's list of moves leaves out what is refused for the slot it is opened on.
- The ENTER menu and a registered team's OK, as under "Rules" for fragment 14.
- Nothing is checked in a battle, and nothing needs to be: no move gets onto a team
  another way. The team's own menu has no check for the same reason.

The moves are `mod/data/clause_moves.inc.c`, held against Pokémon Showdown's data by
the tests: the ones that raise the user's evasion, the ones marked `ohko`, and the
ones that leave the foe `trapped`.

## What a save unlocks, and the five that could not be rented

What a Free Battle between people is missing on a cartridge nobody has played. Looked
for 2026-10-13 by who reads the save file's records of progress: nothing else of a
Free Battle's does. The bytes of record `0x13` (`func_800510CC`: `+1`, `+0x2F` on,
`+0x3F` on, `+0x4B`) are read by the Stadium, the map and the Gym Leader Castle
(fragments 43, 44, 45) and by fragment 75; the two at `+0x54` of record `0x14` are the
gift Pokémon (fragments 30 and 58).

### Stages

- Free Battle's list (fragment 6) has 30 places: Random Select, then 29 stages. Their
  names are text bank 0x2C from 0x1F on: FREE BATTLE, POKé CUP, CHALLENGE CUP, LITTLE
  CUP, PRIME CUP, CLASSROOM, the eight gyms and towns of Johto with TEAM ROCKET among
  them, the ELITE FOUR's four, CHAMPION, the eight of Kanto, SILVER CAVE and VS RIVAL.
  **[C]** on screen, as far as SILVER CAVE.
- **A stage is listed once a battle has been met there.** The save file has a bit for
  each, a `u32` at `+0xC` of record `0x14` (`func_80051138(0)`): `func_80054AA0(bit)`
  tests one and `func_80054AF4(bit)` sets one (`src/517E0.c`). `D_831038E0` has the
  bit of each place on the list, and `func_831000FC` lists place `i` if `i < 3` or
  its bit is set, writing the places listed to `state + 0xAC` and their count to
  `+0xCB`. A new save gets bits `0x17` to `0x1C` (`func_80052928`), the first six
  places. Fragment 20 sets a stage's bit as its battle is introduced
  (`func_826028E0`, by `func_8006AD10` of the mode).
- **The mod lists all 30** by making the "first three" thirty: the two `slti $at,
  $s0, 3` of the loop in `func_831000FC`, changed in place (`mod/stock_patches.txt`).
  The save file is not asked and not written; fragment 20 goes on setting the bits, so
  a save earns its stages for the original game as before.
- The cursor starts on the second place (`D_8009F864`, which also remembers the last
  choice until power off), and the first six places are the same six as on a new
  save, so the tests' A at this step picks the stage it always did.

### Rental tables

Archive 0xB (ROM `0x1708000`) has 72 tables. The first five are rentals (see "Rental
data in ROM"), and a rule set names one by number (`+0x3C`):

| Table | | Rule sets |
|---|---|---|
| 0 | 86, level 5 | Little Cup |
| 1 | 246, level 100: all but Mewtwo, Mew, Lugia, Ho-Oh, Celebi | Anything Goes, VS Rival, Prime Cup |
| 2 | 248, level 100: those and Mew and Celebi | Prime Cup of Round 2 (kind 13) |
| 3, 4 | 246, level 50 (one table under two numbers) | Poké Cup, Gym Leader Castle |

- **Table 2 is not table 1 with two more**: its Pikachu and Psyduck know other moves.
  The other 244 are the same, byte for byte.
- Its Mew and Celebi have no DVs, no Stat Exp, happiness 127 and no PP Ups: the
  weakest a level 100 can be, where most rentals have some of each.
- **Free Battle's Prime Cup is kind 12**, Round 1's (`D_831038FF` has the kinds of
  its first five rule sets: 5, 12, 7, 0, 1), so it never rents from table 2.
- **Mewtwo, Lugia and Ho-Oh are in no rental table.** The rest of the archive is the
  computer's teams, a trainer every 0x98 bytes with six records of the rentals' form
  from `+8` (`func_80071B58`, `func_80071BB8`). The only level 100 ones of the three
  are the Rival's, in tables 33 (Round 1) and 60 (Round 2).

### The mod's table

`mod/src/rentals.c`. The entry screen takes its table as it starts (`func_8130251C`:
`func_80071914(rules)` for the number, then `func_80071B20(archive, number)`, kept at
`D_81331978`), and that second call is pointed at `Mod_RentalTable`
(`mod/asm_patches.txt`).

- In a Free Battle, for table 1, it fills a table of the mod's own and gives that:
  table 1's records as they are, and the mod's five (`mod/data/rental_extra.inc.c`),
  each where its number falls.
- **Mew and Celebi are copies of table 2's**, which the tests hold against the ROM.
  Asking the archive for a table loads it: `func_80071B20(archive, 2)` took 0x1760
  bytes of the main pool, the table and its block's header, for two records of 24
  (found on the 4 MB build, whose test counts the pool's free bytes).
- **Only who the rule set lets enter.** The game's tables have nobody who may not
  enter under the rules that use them, so neither has the mod's: under OU Rules it
  comes to table 1 again, record for record.
- **Not by changing a rule set's table number**: kind 12's record is the Stadium's
  Prime Cup too, and table 2 would change two Pokémon everyone knows.
- **Mewtwo, Lugia and Ho-Oh** are as the game has Mew and Celebi, with the moves of the
  Rival's own in Round 2. His Mewtwo of Round 1 has Hidden Power, which no DVs make
  the weakest there is.
- **The picker needs nothing changed.** A list of rentals has room for 0xFE
  (`func_81307D08` gives each source five arrays, 0x1E apart for a Game Pak's box and
  0xFE for the rentals), the sort's keys are 0x100 bytes on the stack
  (`func_8130A778`), and counts and places are bytes. `func_81307600` fills the
  arrays from the table, and the three orders are by number, by
  `func_800637C0(species)` (the byte before a species' base stats) and by
  `func_80073450(species)` (`D_8009F97F`: the alphabet's, which is the order the
  list opens in). Every species has its keys, the five included.
- The table is 6 KB of the mod's memory, and the mod is in memory for as long as the
  entry screen is. Nothing reads the table after that.

## Pokémon helpers (main segment)

| Address | Role |
|---|---|
| `func_80071E48(mon, rental)` | expand a 24-byte rental entry into a 0x58-byte record (asm, `src/728D0.c`) |
| `func_80071BB8(mons, roster)` | expand up to six roster entries (CPU teams) |
| `func_80071B20(archive, table)` | a table of rental Pokémon by its number, 0 to 4, or NULL |
| `func_80071CD0(mask, bit)` | whether a mask of species has a bit set; species 1 is bit 0 |
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

Happiness (`record + 0x1C`) is read by the battle code for two moves only
(`fragment79_393CA0.c`): Return's power is `happiness * 10 / 25` and Frustration's
`(255 - happiness) * 10 / 25`, 0 to 102 either way. Their power in the move table is 1.
In the Poké Cup table 232 of the 246 rentals have 128 (power 51 for both). The other 14
run from 40 to 210: some carry one of the two moves (Pidgey 210 with Return, Magnemite
40 with Frustration), others neither.

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

## Trainer pictures

- **The pictures** are an archive at ROM `0x02268000`: `+0x0C` a count of 67, then
  `{offset, size}` per trainer (0x10 bytes each); at each offset a count of expressions
  (1 to 3) and for each where its pixels start, plus 8. A picture is 0x2008 bytes: an
  8-byte header (64, 64, format 2) and 64 x 64 16-bit pixels. Trainer 0x40 is the
  player, with two expressions; 0x14 is CAL, Free Battle's first opponent.
- `func_8004E0F0(buffer, trainer, expression)` loads one (allocating when `buffer` is
  NULL) through an archive handle at `D_80097120->0x28`. A screen has that handle only
  if it started its assets with bit 0x40 set (**[I]** from `func_8004C09C(0x43)` in
  fragment 20 and `0x4F` in fragment 12); the entry screen passes `0xF` and has none. The mod's window
  therefore reads the ROM itself (`Trainer_LoadPicture`, with `func_80003F74`, which waits for
  the read) and draws the buffer with `func_8004D19C`.
- **Who gets which** is decided in fragment 20, three times over, each loop taking the
  sides in turn. The screen's own state is `D_82615A80`, with a player every 0x428 bytes
  from `+0xB0`: `+0x00` kind (1 in Free Battle), `+0x02` controller port (negative for
  the COM), `+0x06` a flag for the player's other expression.
  - `func_8260F7FC` (before a battle) and `func_826101B4` (the result after one) load
    both sides' pictures for the screen itself, into `D_8261A490 + 0xC8 + 4 * side`. The
    COM's come from elsewhere (`func_8260F49C`, a table at `+0x58`).
  - `func_826002BC`, as the screen ends, writes a pair `(trainer, expression)` per side
    to `session->0x2C + 0x80 + 4 * side`, for the screens that follow: `func_8006BAC4`
    copies them to the order screen's `arg + 0x880`, and `func_81406AAC` loads them.
  - All three use the same rule for a human: trainer 0x40 with expression 1 (0 when the
    flag is set), or trainer 0x41 for a kind of 2 or more.
  - All three first look at a pair of bytes per side, `session->0x2C + 0x74 + side` and
    `+ 0x78 + side`, and take the picture from there unless the first is -1. The game
    has a function to set them (`func_8006C5AC`, with a 0x16-byte name) that nothing
    calls, and `func_8006BF78` puts them back to -1 before every battle, so they cannot
    be set ahead of time from the entry screen.
- **The session** (`D_8009DF70`) outlives the entry screen and the battle loop: `+0x00`
  the mode (`0x0220` in Free Battle), `+0x08` each side's controller port, `+0x1C` the
  battle's data, `+0x24` the entry screen's settings, `+0x28` the order screen's
  argument, `+0x2C` fragment 20's.
- **The choice** is one byte per controller port at `0x80000358`: 0 for the game's own
  picture, else a trainer's number plus one. Those are the last four bytes of
  `osAppNMIBuffer` (`0x8000031C`, 64 bytes), which libultra zeroes at power on and this
  game never touches. The mod's window writes it; the mod is gone by the time it is read.
- **Reading it** is done by stock code changed in place (`mod/stock_patches.txt`): in
  each of the three functions the human's rule is rewritten in the room it took, to
  look up the port's byte first. The two loaders keep their three relocated calls of
  `func_8004E0F0` where they are and use the last. There is room for a number and no
  more, so a choice always asks for expression 0, the one every trainer has.
- **Every picture has a number**, so that a choice can be any of them all the same. The
  build writes a second directory for the archive at ROM `0x0225B000`, in the padding in
  front of it, and points the archive table's entry (`0x43765C`) there
  (`tools/mod/gen_trainer_faces.py`, called by `modtool.py inject`). Numbers 0 to 66 are
  the stock entries, their offsets 0xD000 more, so every trainer keeps its number and all
  its pictures. Numbers 67 to 157 are the 91 second and third pictures, trainer by
  trainer, each entry leading to a 16-byte block that follows the directory: a count of
  1 and where that one picture is. The loader checks a number against the directory's
  count and reads the block and the picture by adding 32-bit offsets, and that is all it
  uses: not an entry's size, not the archive's. No picture is moved or copied; 4,000
  bytes in all.
  - A stock directory cannot grow where it is: its last entry ends at `+0x440`, where the
    first trainer's block begins.
  - A choice past 0x7F is fine on the way the mod takes: the picture numbers travel as
    halfwords (`sh` in `func_826002BC`, `lh` in `func_8006BAC4` and `func_81406AAC`).
    The signed bytes are the pair at `session->0x2C + 0x74`, which nothing sets.
  - The directory is kept in memory by the screens that open the archive, at 16 bytes an
    entry: 1,456 bytes more than before on the versus card, the order screen and the
    result.
- **A trainer's faces** in the window are that table read the other way:
  `mod/data/trainer_faces.inc.c` has, per trainer, how many pictures, the number of the
  second, and which the window shows first. Left and Right on the picture go round the
  trainers; C Left and C Right go round the trainer's pictures from any row, as the C
  buttons act on the detail panel's moves wherever its cursor is. The window's state
  keeps the trainer and the face, and works the choice out from them.
- **Which face comes first** was decided by looking at them: `DEFAULT_FACES` in the
  generator. With three pictures the game's run upset, pleased, composed; with two,
  mostly upset, composed. The last is what the game shows of CAL before a battle (his
  third) and of the player (their second), so the window starts on the last, except for
  six trainers whose pictures run another way or whose last is not their best, chosen
  from a sheet of them all. Where the game keeps its own choice for
  each of its trainers was looked for and not found: in Free Battle the table at
  `+0x58` of fragment 20's data, which `func_826002BC` reads for the COM, is empty, and
  the pair `(0x14, 2)` is there at `+0x84` by the time the result is up. 17 trainers have
  one picture, 9 have two and 41 three.
- **To look at the pictures**: 64 x 64, 16 bits a pixel (5 each of red, green and blue,
  then one of alpha, always set), and on odd rows each pair of 32-bit words is swapped,
  as in the image banks. The grey frame is part of the picture: 3 pixels at the left and
  top, 4 at the right and bottom, with the trainer on black inside, (3,3) to (59,59).
  A new picture would be one more entry and a block with the picture after it, 8,232
  bytes in all. Five fit behind the directory where it is; a sixth does if the directory
  starts at the very front of the padding, 2,016 bytes sooner, or goes in another gap,
  an entry's offset being free to point anywhere in the ROM.

## Trainer names and titles

- **A side's name** starts on the entry screen. Each team being chosen has one
  (`party + 0x11`, the party at `state + 0x15370`), given by `func_81302EE4(party,
  state, name, id, ...)` when the side's turn begins: a Game Pak's trainer name, or
  none. At OK `func_81300BE8` copies it to `settings + 0x904 + 12 * side`, or "1P" to
  "4P" (text bank 0xF, 0x62 + port) when there is none. From there it goes to fragment
  20's data (`session->0x2C + 0x8D0 + 12 * side`) and to the order screen's argument
  (`+0x850`).
- **In Free Battle fragment 20 names a human again**: `func_82601BB0` formats "%dP" from
  the port over whatever was handed on, so not even a Game Pak's trainer name shows
  there. The other modes go through `func_82601A84` instead, which the mod leaves
  alone and nobody has looked at closely.
- **The mod's name** is eight bytes per controller port at `0x80000334`, empty for none,
  in `osAppNMIBuffer` like the picture (below). Keeping one in the window writes it there
  and to the team being chosen; `Mod_PartyInit` (in place of `func_81302EE4`) gives it
  to the player's team on every later visit; and `func_82601BB0` is patched to write
  the port's name, when it has one, in place of "%dP". It writes it rather than
  trusting what was handed on: the Challenge Cup goes from the rule select straight to
  fragment 20 (`func_80068E14`, when `func_8006A3E0` gives 2), so no entry screen fills
  `settings + 0x904`, and a player with a name was shown none there (found 2026-10-13).
  Afterwards `func_8006B0B8` copies fragment 20's names back to the settings on that
  path. Seven characters, a Game Boy trainer
  name's length: twelve bytes a side is the room downstream, but the order screen's
  name plate is narrow.
- **A title** is a number in text bank 0x48 (ROM `0x01D95240`: a count of 70, that many
  offsets from the bank's start, then the texts). The numbers run as the Game Boy games'
  trainer classes do, many sharing a text (RIVAL nineteen times), the last few empty. A
  human's is always 0x29, POKéMON TRAINER, written as a constant where the versus card
  (`func_826053A4`) and the result (`func_82605908`) look the text up with
  `func_8004C874(0x48, number)`; each has the side's port in hand just before, to tell a
  human from the COM, whose title comes from its trainer's data.
- **The mod's title** is a byte per port at `0x80000354`, the number XOR 0x29 so that a
  byte nobody has set gives the stock title. The two lookups are patched to read it. The
  window steps through one number per different text, the player's own first
  (`tools/mod/gen_trainer_titles.py` → `mod/data/trainer_titles.inc.c`, 40 of them), and
  reads the text from the ROM, the bank not being loaded on the entry screen.
- **`osAppNMIBuffer`, as the mod uses it**: `0x80000330` whether Free Battle's rule
  set is the mod's (see "OU Rules"), `0x80000334` names (4 x 8), `0x80000354` titles
  (4), `0x80000358` pictures (4). The first 0x14 bytes are untouched.
  `mod/tests/test_trainer_pictures.py` checks the layout against the patches.

## Names

A record's nickname (`+0x34`) and OT name (`+0x40`) are zero-terminated strings in the
game's own character codes: ASCII, plus Latin-1-like codes above 0x90 for the signs
(`×` 0xD7, PK 0xBC, MN 0xBD, ♂ 0xA9, ♀ 0xBE, `é` 0xE9).

- **Game Boy codes.** `D_80097680` points at a 256-byte table from Game Boy character
  codes to the game's: `D_80097380` for English, `D_80097480` and `D_80097580` for the
  other language groups (`func_800609D0`). 0x80 marks a code with no character.
  `func_80060B28` goes the other way by scanning the table from the start.
- **Registered teams** store names in Game Boy codes (`func_800615D0` →
  `func_80060EC8`, through an 11-byte buffer ended by 0x50). So a name is at most ten
  characters and may only use characters the table has, or it does not survive saving.
- **No nickname** is stored as the species name (`func_8004B7A4(species)`), which is what
  `func_80071E48` gives a rental. `func_8003F5AC` compares the two to decide on the tint,
  so renaming a rental tints it, as nicknaming does in the stock game, and renaming it
  back removes the tint. The model and list icon are reloaded after a rename.
- **Text is drawn through printf** (`func_800495BC`, `func_80049148` call `_Printf`), so a
  `%` in a name would be read as a format. The keyboard has no `%`.
- **Font.** `D_80126F5C` and `D_80126F60` point at the glyph tables for codes 0x20–0x7F
  and 0x90–0xFF (0 = no glyph). In the picker every keyboard character has one; `<`, `>`
  and `_` do not.
- **Fragment 77 is a developer "PokeMon Editor"** left in the ROM (pool tag `PMED`; menu
  strings Item, Move1–4, Name, Parent, Friend, Level and so on). Its name-entry character
  table is at ROM `0x36C89C`. It is a debug text screen and nothing here uses it, but it
  was the confirmation that these codes are what the game itself types into a name.

The keyboard's keys are generated by `tools/mod/gen_name_keys.py` into
`mod/data/name_keys.inc.c`: the Gold/Silver/Crystal nickname screen, plus ♂ and ♀ from
Red/Blue/Yellow in the two cells Crystal leaves empty. `mod/tests/test_name_keys.py`
checks the set against both cartridge layouts and every code against the ROM's table.

## Memory

`Util_InitMainPools` gives the main pool everything from `D_80134470` to the end of RAM
as reported by `osGetMemSize()`: about 2.9 MB without an Expansion Pak, 7.1 MB with one.
`D_800871F4` holds the RAM size and `D_800871F0` the amount above 4 MB. The pool's free
byte count is at `D_800CCDB0 + 0x1C` (`0x800CCDCC`).

The entry screen (`func_813029F0`, fragment 14's only way in) pushes the pool state,
loads its assets, calls `func_8130251C` (the mod's boot hook, so the mod fragment is
allocated inside that state) and pops the state on the way out, which frees the mod.

Measured in the rental picker with the mod loaded (0xDDB0 bytes at `0x80253290`, of
which 0x2008 are the trainer window's picture): with 4 MB of RAM the pool has `0x1E350`
bytes free (124 KB). With 8 MB it has exactly 4 MB more (measured on an earlier build,
whose mod was 0x4AC0 bytes: `0x427CB0` against `0x27CB0`).

The figure does not move while a rental is opened, edited, renamed, made shiny and
entered, or while the trainer window reads a picture and a title: the screen and the mod
allocate what they need up front. Without the mod the 4 MB figure would be 38 KB higher
(`0x2C780`). In the battle that follows, 4 MB leaves `0x1E2A0` free, with the mod
unloaded (from an earlier build; the mod is not in memory by then).

Free Battle's rule select and the rule viewer each load a copy of the mod for a call
(two for the rule select, as it starts and as it ends), and RULE EDIT keeps one. All
are light screens: the rule select has `0x4BA660` bytes free with 8 MB, the viewer
`0x4CD2B0`, RULE EDIT `0x4D20D0`, each 4 MB less without the Expansion Pak, against
57 KB a copy. A `call` thunk has nothing to fall back on if a copy cannot be loaded,
the function it stands for being in the copy.

BizHawk's Ares64 core always has 8 MB. `tools/mod/make_4mb_rom.py` writes a test copy of
a ROM whose `osGetMemSize()` returns 4 MB; run it from power on, not from a savestate.

## Fragment map

`D_800CC630`: 240 entries of `{base, size}`, indexed by fragment ID. `Memmap_GetFragmentVaddr`
translates any address in `0x81000000–0x90000000` through it. ID 0x40 (vram `0x85000000`)
is unused by all 88 stock fragments. **[C]**

## Tests

Three layers, cheapest first. All three should pass before and after any change to the
build tools or to the commit of the decompilation the mod sits on.

    python3 -m unittest discover -s mod/tests       # tools and checksums; WSL or Windows; seconds
    python3 tools/mod/checksums.py check            # the built mod against the record
    python3 -m unittest discover -s mod/tests/emu   # the game in BizHawk; Windows; about 25 minutes

1. **Tool tests** (`mod/tests/test_*.py`): the ROM checker, relocation tool, injector,
   patch tool, the generated move, keyboard, trainer title and trainer face tables, what
   the mod assumes about the ROM's trainer pictures, and the directory it gives them,
   read the way the game reads one; what it assumes about the stage list and the rental
   tables, and its five rental Pokémon against the game's own and the Rival's team; the clauses' moves against Pokémon Showdown's data
   and the game's names for them, and the mod's rule set against the game's records.
   One asks the decompilation's sources whether every hooked function is still
   assembly there, which an old extract can hide.
2. **Checksums** (`mod/checksums.txt`): SHA-1 of the original ROM, the mod ROM and the
   patch. The build is repeatable, so the same sources always give the same bytes.
   `build_mod.sh` reports the comparison at the end of every build, and
   `mod/tests/test_checksums.py` fails on a difference. When the mod's sources change on
   purpose, `tools/mod/checksums.py update` records the new build. An unchanged checksum
   after rebasing onto a newer decompilation proves the mod did not change.
3. **Emulator tests** (`mod/tests/emu/`): the editor played by script, with checks on
   game memory. `harness.py` switches the console on with no save data, walks to the map
   and saves a state; each *scene* (the picker under Anything Goes, under Poké Cup rules,
   and for player 2) is reached from there once and saved, and every test starts from a
   scene's state.
   - `test_editor.py`: opening and closing, DVs, Stat Exp, level, the move list, shiny,
     Hidden Power, the keyboard.
   - `test_teams.py`: the edited record in the party and in battle; a registered team
     after a power cycle; the editor on one of the team, by both ways in; Poké Cup's
     level range and level total; two players.
   - `test_items.py`: what the ITEM list offers, and an item from it reaching the party.
   - `test_trainer.py`: Change Trainer, its window and keyboard, and the picture, name
     and title on the screens up to and after a battle, for one player and for two.
   - `test_clauses.py`: the mod's rule set on Free Battle's list and in the viewer; a
     rental and a registered team refused for a move, and the editor's list of moves;
     Anything Goes as it was; RULE EDIT's rows, and a rule set saved with clauses.
   - `test_unlocks.py`: on the empty save, Free Battle's 30 stages and the 251 rentals;
     the five opened, one edited and entered, one registered; what OU Rules and the
     Poké Cup list.
   - `test_without_expansion_pak.py`: the 4 MB test ROM.
   - Stats are compared with the Generation 2 formula worked out in Python from the base
     stats in the ROM; the move list with `mod/data/legal_moves.inc.c`; a saved name
     with the Game Boy codes in `gen_name_keys.py`.

What the editor draws cannot be read from memory, so `screens.py` hashes the editor
window's pixels in a screenshot and compares with `mod/tests/emu/screens.json` (hashes
only; the screenshots are not kept). The emulated picture has noise that changes every
frame, so this only works because test runs are frame-exact (below). A hash therefore
also changes when the button presses leading up to its screenshot change. After looking
at the new screenshots in `.emu/test/remote`, `UPDATE_SCREENS=1` re-records them.

The noise is the emulator's video output dithering the picture (one step of a colour,
all over the screen, the border included), from a random sequence that every frame
shown since power-on has drawn on. A screenshot's hash therefore holds only while the
same pictures come on the same frames, and a battle breaks that from one build of the
mod to the next: its first picture, where the video mode goes from 640 to 320 wide, came
on frame 6341 of the test in one build and 6342 in another, with the mod not even in
memory by then. The game is back in step before the battle is left and the result
appears on the same frame either way, but the sequence is a frame's worth out for good,
so `result_named` hashed to one of two values depending on the build while looking the
same. Waiting for the screen does not help: nothing about the game differs by then. So a
screen after a battle is checked in the game's own frame buffer instead
(`Session.drawn`, `screens.check_drawn`): the one being shown is `__osViCurr->framep`
(`0x800A1530`, +4), 640x480 at 16 bits like the screenshot of a menu, and what the game
drew there is the same in every build and on every frame. Two things found on the way:
BizHawk's memory domain `System Bus` reads the video registers at `0x04400000`, and
there is no `VI Register` domain on Ares64.

### Moving to a newer base

The mod only depends on the decompilation for the game's symbols, the build tools, and
the assembly of the functions it hooks (`mod/hooks.txt`) or changes in place
(`mod/stock_patches.txt`). Before rebasing, compare
the old and new base:

    git fetch origin
    git diff --name-only <base> origin/master -- . ':!src' ':!docs' ':!COVERAGE.md'    # build or tools changed?
    git diff --name-only <base> origin/master -- src/fragments/14/fragment14_FA520.c \
        src/fragments/14/fragment14_104FC0.c src/fragments/14/fragment14_FD770.c \
        src/fragments/14/fragment14_FAD40.c src/fragments/14/fragment14_109280.c \
        src/fragments/20/fragment20_1280F0.c src/fragments/20/fragment20_128B10.c \
        src/fragments/20/fragment20_12C460.c \
        src/fragments/6 src/fragments/82 src/fragments/83 src/517E0.c \
        hand_asm                                                                        # hooked code changed?

If both are empty, rebase, rebuild (`wsl_build.sh`, then `wsl_build.sh mod`) and run the
three test layers. The checksums should not change. If a hooked function has been
decompiled, a fresh extract no longer writes its `.s` file, which `modtool.py` needs (an
old copy may linger in `asm/` and hide this until the next `wsl_build.sh init`); if a
symbol the mod uses was renamed, the mod fails to link and `mod/include/game.h` needs
the new name.

2026-10-11, `e06da865` → `e82d7f7`: both comparisons empty, no conflicts, the stock ROM
matched, and the mod ROM and patch were byte for byte the same as before.

2026-10-13, `e82d7f7` → `3bda6f8b`: the first comparison lists only two upstream CI
workflows, the second is empty, and the rebase had no conflicts. 61 functions were
decompiled, none of them hooked, patched or called by the mod, and no symbol was renamed.
The tool tests pass; not yet rebuilt or run in the emulator (no ROM in that checkout).

## Releases

A release is the patch and nothing else: never a ROM, patched or not, and nothing made
from one (the ELF, extracted assembly, savestates). GitHub adds the source archives.

Building the patch takes the original ROM, so GitHub cannot build it, and the patch is
not kept in the repository either. `.github/workflows/mod-release.yml` drafts the release
and whoever has the ROM attaches the patch they built:

1. Build and run the three test layers. If the mod changed, `checksums.py update`.
2. Add a `## vX.Y.Z` entry at the top of [CHANGELOG.md](CHANGELOG.md), written for someone
   who plays the mod. `python3 tools/mod/release_notes.py` prints the notes as they will
   appear.
3. Commit, then tag that commit and push both:

       git tag v0.1.0
       git push <remote> rental-editor v0.1.0

   The tag's run creates the draft "Rental editor v0.1.0". Its notes are the changelog
   entry, the patching instructions and the checksums from `mod/checksums.txt`. A tag
   with a hyphen (`v0.2.0-rc1`) is marked a pre-release. A tag with no changelog entry
   fails and drafts nothing; add the entry, then delete and push the tag again.
4. From the checkout the tag was made in, attach the patch and publish:

       python3 tools/mod/checksums.py check
       gh release upload v0.1.0 build/stadium2-rental-editor-us.bps
       gh release edit v0.1.0 --draft=false

   Publishing starts one more run, which fails if anything but the patch is attached or
   if the patch is not the one in the tag's `mod/checksums.txt`. The release is public by
   then, so a failure means: replace the file.

- **Branches.** `master` only follows the decompilation and takes no commits of ours. The
  mod lives on `rental-editor`, which is the default branch of the repository it is
  published from. Rebasing it onto a newer base rewrites its commits, so a release's tag
  is what keeps that release's commit.
- **Front page.** `.github/README.md` is what GitHub shows for the repository: it takes
  a README there in preference to the one in the root. That leaves the decompilation's
  `README.md` untouched, so it never conflicts in a rebase. Links in it are relative to
  `.github/`. Its screenshots are in `mod/images/`: test screenshots from
  `.emu/test/remote`, reduced to 256 colours with Pillow
  (`image.quantize(256, method=Image.Quantize.FASTOCTREE)`, saved with `optimize=True`),
  which gives the same bytes every time. Six are shots the emulator tests take:
  `menu` is `edit_entry`, `editor` is `fields_shiny`, `moves` is `list_hidden_power`
  and `keyboard` is `keyboard_upper`; `clause` is `clause_refused` and `rule_edit` is
  `rule_page_clauses`, from `test_clauses.py`. `team_menu`, `team`, `trainer` and `versus` were
  taken by hand in one sitting, with three rentals on the team (Abra, Aipom and
  Alakazam), so that they tell one story; the
  last two were taken again for v0.4.0 by a script through the tests' harness, with the
  same team, the tenth in the ring, ASH and GYM LEADER: `versus` has to show the picture, name and title that `trainer` shows being
  chosen (the tests' own `versus_named` keeps the default picture, and beside the
  window it looks as if the choice had not been kept). Before a release,
  reduce the tests' fresh shots the same way and compare: a picture that no longer
  comes out the same is out of date (`moves` was, for v0.2.0, by one number).
- **Why a changelog by hand.** After a rebase every commit of the mod is new, and between
  two tags lie hundreds of decompilation commits, so notes generated from the commit log
  or from pull requests would be wrong.
- **The decompilation's workflows** (ROM gate, coverage, baseline image) belong to
  `michiiik/pokestadiumgs` and its self-hosted runner. In another repository they fail
  or wait for a runner that never comes; switch them off there with
  `gh workflow disable`, which leaves the files alone so a rebase stays clean.

## Emulator harness

`tools/mod/emu.py` drives BizHawk through `mod/lua/remote.lua` (press, wait, shot, save,
load, read, find, write, eval, reboot). BizHawk lives in `.emu/BizHawk`; output goes to
`.emu/remote`, or `.emu/test/remote` for the tests. Run it with Windows Python.

- **Frame-exact runs.** Normally the game runs freely between commands. With
  `S2_REMOTE_STEP=1` (`Emulator(stepping=True)`, which the tests use) the script pauses
  the game whenever no command is running, so the game sees exactly the frames the
  commands ask for. After one `reboot` to start counting from frame 0, two runs of the
  same commands are identical: same frame numbers, same memory, same pixels.
- **The tests never touch the user's settings.** They pass BizHawk `--config=` a copy
  (`.emu/test/config.ini`) with two controllers plugged in, and run a copy of the ROM
  under its own name so its save file starts empty.
- `reboot` power-cycles the console; the frame counter goes back to 0 and the script
  keeps running. `client.reboot_core()` called in the middle of a batch ends the batch
  there with no output, so the command only notes the request and the reboot happens
  once the batch's output is written.

- Use the **Ares64** core (`"N64": "Ares64"` in `config.ini`). The default Mupen64Plus core
  runs the game but renders black.
- Memory-write callbacks register but never fire on Ares64, so there are no breakpoints;
  use `find` and static reading instead.
- With no audio device (a locked or remote session) BizHawk stops at an "Initialization
  Error" box about the sound device before the Lua script runs. `emu.py` presses its OK
  button while it waits for the script.
- Path to the picker: Start, Start, A, A (map); D-pad Right, Up, A (Free Battle); A, A, A
  (1P vs COM, Normal); A (Anything Goes); A (stage); Right, Right, A (Rental Only).
  Against a second player there is no difficulty to pick, so that path is one A shorter.
  `mod/tests/emu/harness.py` has these as `BOOT`, `FREE_BATTLE` and `SCENES`.
- `tools/mod/emu.py script mod/lua/goto_rental.txt` replays that path from `whitecity`.
- The picker lists the rentals by name, four to a row, not in the rental table's
  order: Diglett is the first of the tenth row, or the second under Anything Goes,
  where Celebi comes before it. `harness.to_rental(species, listed)` gives the presses
  to any of them.
- Free Battle's rule sets: the fourth A of that path opens them with the cursor on
  Anything Goes; Down five times and A opens the list of the player's own. R is "Check
  Rules".
- RULE EDIT: Start, Start, A ("Please Select", with the cursor on the map); Left, Up
  (OPTIONS), A; Down twice, A. "Make rules" then wants A twice, for a place on the
  list and then the page. `harness.py` has these as `SELECT`, `RULE_EDIT` and
  `MAKE_RULES`.
- A savestate carries the cartridge's save data with it, so to test saving, `reboot` and
  walk in from the title screen instead of loading one.
- `player 2` makes the following presses come from controller 2. That needs
  `"P2Controller": 1` in the Ares64 section of the config, and savestates made with one
  controller then stop loading (the load reports success and changes nothing).
  `emu.make_config` writes such a config without changing the user's.
- Hand-made savestates in `.emu/remote`: `whitecity`, `fb_rules`, `fb_entry`, `fb_rental`
  (stock ROM). A state taken with fragment 14 loaded contains that build's mod code, so
  after rebuilding start from `whitecity`, which predates the entry screen. The tests
  use none of these.
- The fragment map is indexed by fragment *id*, not by the number in the source file's
  name: "fragment 14" is linked at `0x81300000`, so its id is 3 and its entry is at
  `D_800CC630 + 3 * 8`.
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

Tests: `python3 -m unittest discover -s mod/tests` (157 tests, of every tool).

## Open questions (milestone M1)

Answered: the rental expander (`func_80071E48`), what registered teams store (full
data), the fragment map (240 entries, ID 0x40 free), the ENTER menu's handlers and that
they are shared by every mode, that an edited record reaches battle, that a
registered edited team loads back unchanged after a reset, and how the ITEM list works
(see "Item list"). Remaining:

1. Where cup level rules are stored (`D_82B0865C` and the rule flag word are leads).
2. Whether EDIT behaves in the Stadium cups and Gym Leader Castle, which use the same
   entry screen under other rule sets.

Players pick one after another on the same screen, each with their own controller
(`panel->0x37`), so the editor's single state is enough.
