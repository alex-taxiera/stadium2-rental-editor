# Pokémon Stadium 2 rental editor

A patch for Pokémon Stadium 2 (USA) that adds an **EDIT** entry to the menu shown when
you pick a rental Pokémon. It opens an editor for the rental's moves, level, DVs and
Stat Exp, limited to what the Game Boy games allow, and the edited Pokémon is what
enters the battle or the registered team.

The patch is a BPS file. It contains only the changes, not the game.

## Applying the patch

You need your own Pokémon Stadium 2 (USA) ROM:

| | |
|---|---|
| Game ID | `NP3E`, revision 0 |
| Size | 64 MB (67,108,864 bytes) |
| SHA-1 | `d8343e69a7dc63b869cf6361d87cde64444281d3` |

Apply `stadium2-rental-editor-us.bps` with any BPS patcher (Floating IPS, Rom Patcher
JS), using a `.z64` ROM. Or use the one in this repository, which also takes `.v64` and
`.n64` dumps and always writes `.z64`:

    python3 tools/mod/bps.py apply <your-rom> stadium2-rental-editor-us.bps stadium2-rental-editor.z64

A BPS patch carries checksums of the ROM it expects and of the result, so a patcher
refuses the wrong ROM and tells you if the output is wrong. `bps.py info <patch>` prints
both.

The save format is untouched. The header keeps the game ID `NP3E`, which is what ares and
most flashcart firmware use to choose the save type (Flash RAM). The header checksum does
change, so anything that looks the game up by checksum will not recognise it; set Flash
RAM by hand there.

## In the game

On any screen where Pokémon are entered (Free Battle, registering a team), go to the
rental tab (**R**), press A on a rental, and choose **EDIT** under Yes / No / ITEM. In a
two-player battle each player edits in turn with their own controller.

The editor covers the party box; the game's own panel underneath shows the Pokémon as it
will be, with stats recalculated as you change things.

| Where | Button | Does |
|---|---|---|
| Moving around | D-pad | move between moves, level, DVs and Stat Exp |
| | A | change the field under the cursor |
| | B | close the editor, back to Yes / No |
| On a number | Up / Down | one step (hold to repeat) |
| | Left / Right | a bigger step: 4 for DVs, 10 for level, 8 steps for Stat Exp |
| | L / R | lowest / highest value |
| | A or B | done |
| In the move list | Up / Down | one move (hold to repeat) |
| | Left / Right | a page |
| | A | take the move |
| | B | back without changing |

What can be changed:

- **Moves.** Any move the species or an earlier evolution learns in Red, Blue, Yellow,
  Gold, Silver or Crystal by level, TM/HM, tutor or breeding. Event-only moves are left
  out. A slot can be emptied as long as one move remains, and a move cannot be taken
  twice. PP is set to the new move's full PP.
- **Level**, within the range of the rules in force (and never below 2). The game's own
  checks on a team, such as the Poké Cup's level total, still apply when you enter it.
- **DVs** for Attack, Defense, Speed and Special, 0–15. The HP DV follows from the other
  four and is shown greyed.
- **Stat Exp** for all five stats, 0–65535, in the 64 steps that change the stat.
- **Held item**: use the game's own ITEM entry, as before.

The top line of the editor shows what the DVs decide besides stats, each only when it
applies: the gender symbol, `SHINY`, Unown's letter, and Hidden Power's type and power
when the Pokémon knows the move. A rental made shiny looks shiny everywhere, battle
included.

A registered team keeps its edits.

## Known limits

- An edit belongs to the Pokémon's entry in the list. If you scroll the list a long way
  before choosing Yes, the entry is rebuilt from the rental table and the edit is gone.
  Edit, then enter.
- Outside the editor the game labels Hidden Power as Normal, as the original does.
- Moves are checked one at a time. Combinations that cannot exist on one Pokémon in the
  Game Boy games are not rejected.
- Nicknames cannot be changed.
- Only rentals get EDIT, not Pokémon read from a Game Pak.
- USA version only.

## What has been tested

Everything below was run in BizHawk 2.x with its Ares64 core, driven by scripts
(`tools/mod/emu.sh`).

- Moves, level, DVs and Stat Exp edited and carried into a battle.
- Shiny, gender, Unown's letter and Hidden Power shown and updated as DVs change.
- A registered team reloaded after a console reset with its edits intact.
- EDIT from Free Battle and from Register POKéMON.
- Under Poké Cup rules the level stops at 50 and 55.
- A second player editing with controller 2, with controller 1 ignored meanwhile.
- A build made to believe the console has 4 MB of RAM (`tools/mod/make_4mb_rom.py`): the
  entry screen keeps 163 KB of its memory pool free with the mod loaded, the editor
  allocates nothing, and the battle starts normally.
- The original ROM still builds byte for byte from the same tree, and the patch applied
  to it reproduces the modified ROM.

Not tested: real hardware, standalone ares, other emulators, the Stadium cups and Gym
Leader Castle (they use the same entry screen), and the Japanese version.

## Checklist for real hardware

1. Patch a clean ROM and copy the `.z64` to the flashcart. If the cart does not pick a
   save type by itself, it is Flash RAM, the same as the original game.
2. Boot it. The title screen and menus should be exactly as in the original.
3. Free Battle → 1P vs COM → Anything Goes → **Rental Only**. Reaching the picker means
   the mod's code was loaded.
4. A on a rental, then down to **EDIT**, A. The editor window opens over the party box.
5. Change a move, a DV, a Stat Exp value and the level. The stats in the lower panel
   follow each change.
6. Set Attack, Defense, Speed and Special DVs to 10. `SHINY` appears and the Pokémon in
   the lower panel changes colour.
7. B, then Yes. The party box shows the Pokémon; Start, OK.
8. Pick the opponent's team and start the battle. Check the moves and HP in battle.
9. Leave and come back to the picker a few times, including after a battle.
10. Two players: Free Battle → 1P vs 2P. Player 2 edits with controller 2.
11. Start → **OK to Register**, switch the console off and on, and load the team from
    Registered POKéMON.
12. Repeat steps 3–8 with the Expansion Pak removed (or fitted, whichever you did not
    start with).

If something goes wrong, the useful details are the step, whether the Expansion Pak was
fitted, the flashcart and its firmware, and what was on screen: a freeze on entering the
picker points at loading the mod, a freeze on opening the Yes / No menu at the hooks, and
leftover graphics after closing the editor at the redraw.

## Building

See "Building" in [NOTES.md](NOTES.md). In short, inside WSL:

    python3 tools/mod/check_rom.py <path-to-rom>   # verify the ROM and install it as the base
    tools/mod/wsl_build.sh init                    # first time only
    tools/mod/wsl_build.sh mod                     # build/stadium2-rental-editor-us.bps

The mod leaves the decompilation's sources untouched. Its code is one new overlay stored
in an unused part of the ROM, and three functions of the entry screen are replaced by
jumps into it. [NOTES.md](NOTES.md) has the details.

This is built on [michiiik/pokestadiumgs](https://github.com/michiiik/pokestadiumgs), a
fork of [pret/pokestadiumgs](https://github.com/pret/pokestadiumgs). Move legality comes
from Pokémon Showdown's Gen 2 learnsets and the pret Gold and Crystal disassemblies.
