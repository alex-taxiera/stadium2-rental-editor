# Pokémon Stadium 2 rental editor

A patch for Pokémon Stadium 2 (USA) that adds an **EDIT** entry to the menu shown when
you pick a rental Pokémon. It opens an editor for the rental's nickname, moves, level,
happiness, DVs and Stat Exp, limited to what the Game Boy games allow, and the edited
Pokémon is what enters the battle or the registered team. It also gives the game's rules
three move clauses, and Free Battle a rule set that has them.

![The editor open on a rental Abra](images/editor.png)

The patch is a BPS file. It contains only the changes, not the game.

## Applying the patch

You need your own Pokémon Stadium 2 (USA) ROM:

| | |
|---|---|
| Game ID | `NP3E`, revision 0 |
| Size | 64 MB (67,108,864 bytes) |
| SHA-1 | `d8343e69a7dc63b869cf6361d87cde64444281d3` |

The patch is attached to each release on this repository's Releases page.
[CHANGELOG.md](CHANGELOG.md) says what each release changed.

Apply `stadium2-rental-editor-us.bps` with any BPS patcher (Floating IPS, Rom Patcher
JS), using a `.z64` ROM. Or use the one in this repository, which also takes `.v64` and
`.n64` dumps and always writes `.z64`:

    python3 tools/mod/bps.py apply <your-rom> stadium2-rental-editor-us.bps stadium2-rental-editor.z64

A BPS patch carries checksums of the ROM it expects and of the result, so a patcher
refuses the wrong ROM and tells you if the output is wrong. `bps.py info <patch>` prints
both.

The save file is laid out as the original's. One thing in it is new: a rule set of your
own keeps its move clauses in a byte of its saved form that the original leaves empty
(see "Rule sets and move clauses"). The header keeps the game ID `NP3E`, which is what ares and
most flashcart firmware use to choose the save type (Flash RAM). The header checksum does
change, so anything that looks the game up by checksum will not recognise it; set Flash
RAM by hand there.

## In the game

On any screen where Pokémon are entered (Free Battle, registering a team), go to the
rental tab (**R**), press A on a rental, and choose **EDIT** under Yes / No / ITEM. In a
two-player battle each player edits in turn with their own controller.

A rental that is already on your team can be edited where it is, without taking it off
the team and choosing it again. Once your team is chosen, Start brings up the usual menu
(OK, OK to Register, ...), which has two more entries. **Edit POKéMON** puts the cursor
in the team's box: A on a rental opens the editor on it, B closes the editor for the next
one, and B again goes back to the menu. The game's own **Reselect some POKéMON** leads to
the same place by another road: its EXCHANGE menu has **EDIT** under Yes / No. Either
way the edits are made to the Pokémon on the team, and everything changed before it was
entered is still there.

| | |
|---|---|
| ![The team's menu, with Edit POKéMON and Change Trainer](images/team_menu.png) | ![The cursor in the team's box, under "Edit which POKéMON?"](images/team.png) |

The other new entry is **Change Trainer**. It opens a window with three things to change,
Up and Down moving between them:

![The trainer window: a picture, the name ASH and the title GYM LEADER](images/trainer.png)

- your **picture**: Left and Right step through every trainer in the game. The first one
  in the ring is the game's own choice for you. Most trainers have two or three faces,
  and C Left and C Right go round them, wherever the cursor is: the line under the
  window shows the two buttons and "Face" whenever there is more than one. That is every
  picture of a trainer in the game, 158 of them.
- your **name**, in place of 1P to 4P: A opens the editor's keyboard, for up to seven
  characters. An empty name gives the game's back.
- your **title**, in place of POKéMON TRAINER: Left and Right step through the forty
  titles the game gives its own trainers, GYM LEADER, RIVAL and ROCKET among them.

A on the picture or the title keeps all three and B leaves them as they were. They are
then yours on the screens before and after each battle, for every battle until the
console is switched off. Each player chooses their own, with their own controller.

The editor covers the party box; the game's own panel underneath shows the Pokémon as it
will be, with stats recalculated as you change things. The field the cursor is on has the
game's own brackets around it, which turn green while you are changing a number. The move
list has a scroll bar, and a hand points at the move the cursor is on.

| Where | Button | Does |
|---|---|---|
| Moving around | D-pad | move between moves, level, happiness, DVs and Stat Exp; Up from the top row reaches the name |
| | A | change the field under the cursor |
| | B | close the editor, back to Yes / No, or to the team's box after Edit POKéMON |
| On a number | Up / Down | one step (hold to repeat) |
| | Left / Right | a bigger step: 4 for DVs, 10 for level, 25 for happiness, 8 steps for Stat Exp |
| | L / R | lowest / highest value |
| | A or B | done |
| In the move list | Up / Down | one move (hold to repeat) |
| | Left / Right | a page |
| | A | take the move |
| | B | back without changing |
| On the keyboard | D-pad | move between keys (hold to repeat; wraps at the edges) |
| | A | type the key, or use `lower` / `UPPER`, `DEL`, `END` |
| | B | delete the last character; with none left, back without changing |
| | L or R | switch between upper and lower case |
| | Start | jump to `END` |

What can be changed:

- **Nickname**, up to 10 characters, on a keyboard laid out like the Game Boy's. It
  offers what a nickname can be typed with in Red, Blue, Yellow, Gold, Silver or Crystal:
  letters in both cases, space, `- ? ! / . ,`, `× ( ) : ; [ ]`, the PK and MN signs, and
  ♂ ♀. `END` with nothing typed gives the species name back. As in the original game, a
  nicknamed Pokémon is tinted a slightly different colour, so a rename changes how it
  looks.
- **Moves.** Any move the species or an earlier evolution learns in Red, Blue, Yellow,
  Gold, Silver or Crystal by level, TM/HM, tutor or breeding. Event-only moves are left
  out. A slot can be emptied as long as one move remains, and a move cannot be taken
  twice. PP is set to the new move's full PP.
- **Level**, within the range of the rules in force (and never below 2). The game's own
  checks on a team, such as the Poké Cup's level total, still apply when you enter it.
  For a Pokémon already on the team, the level stops where the team would go past that
  total, because the game's answer to a team past it is to have you choose its last
  Pokémon again.
- **Happiness**, 0–255, beside the level. It decides the power of Return, which grows
  with it, and of Frustration, which grows without it, each up to 102. While the cursor
  is on it the top line shows both, and the move list shows them for those two moves.
  Most rentals start at 128, which gives both moves a power of 51.
- **DVs** for Attack, Defense, Speed and Special, 0–15. The HP DV follows from the other
  four and is shown greyed.
- **Stat Exp** for all five stats, 0–65535, in the 64 steps that change the stat.
- **Held item**: use the game's own ITEM entry, as before. Its list now has every item
  the game counts as worth holding in a battle, 42 of them, where the original offers six
  berries plus whatever a connected Game Pak owns. That goes for every Pokémon on the
  screen, not only rentals. The game's own limits still apply: an item a team-mate
  already holds, or one that only works for another species, cannot be taken.

The top line of the editor shows what the DVs decide besides stats, each only when it
applies: the gender symbol, `SHINY`, Unown's letter, and Hidden Power's type and power
when the Pokémon knows the move. A rental made shiny looks shiny everywhere, battle
included.

A registered team keeps its edits. A trainer's picture, name and title are not saved:
they last until the console is switched off.

## Rule sets and move clauses

The game's rules say which Pokémon may enter, at what levels and with what items. The
patch lets a rule set also keep moves out, by three clauses:

- **Evasion**: no Double Team or Minimize.
- **One-hit KO**: no Fissure, Guillotine or Horn Drill.
- **Baton Pass with trapping**: no Pokémon may know Baton Pass together with Mean Look
  or Spider Web. Either alone is fine.

**OU Rules** is a rule set with all three, in Free Battle: on "Please Select Rules" go
down to **Edit Rules**, the last of the six, and it is on the list that opens, after any
rule sets of your own. It is Anything Goes, with any number of Pokémon up to six, levels
up to 100, held items, rentals, registered teams and one to four players, except that
Mewtwo, Mew, Lugia, Ho-Oh and Celebi may not enter, as in the Poké Cup, and the three
clauses hold. R on it, "Check Rules", lists what it says like any rule set; the last
line, **Moves that cannot be known**, has the clauses behind it.

![Diglett under OU Rules: Yes and FISSURE greyed out, the hand on EDIT](images/clause.png)

Under a rule set with clauses:

- The editor's list of moves leaves out what the clauses keep out, Baton Pass while the
  Pokémon knows Mean Look or Spider Web in another slot, and those two while it knows
  Baton Pass.
- A Pokémon that knows such a move cannot be entered. Its menu opens with **Yes** greyed
  out, as the game greys it for an item the rules reject, and the move's name is grey in
  the panel under it. For a rental the hand starts on **EDIT**: change the move, and Yes
  is back. ITEM is refused meanwhile, since choosing an item enters the Pokémon.
- A registered team with such a Pokémon on it, or with one the rules keep out, cannot
  be chosen: the **OK** of its menu is greyed out. **Check** shows its Pokémon, the move
  in grey. The teams OU Rules offers are the ones registered under Anything Goes.

A rule set of your own can have the clauses too. **RULE EDIT**, under OPTIONS, has
three more questions on a rule set's page, after "Hold identical items?": **Use evasion
moves?**, **Use one-hit KO moves?** and **Use BATON PASS with trapping?**, each answered
"Use" or "Don't use" with A. They are saved with the rule set.

![RULE EDIT's page for a rule set, with the three questions](images/rule_edit.png)

As in the original, a rule set of your own is for Pokémon from a Game Pak: it takes no
rentals, and three of six fight.

## Known limits

- An edit belongs to the Pokémon's entry in the list. If you scroll the list a long way
  before choosing Yes, the entry is rebuilt from the rental table and the edit is gone.
  Edit, then enter.
- The team's copy and the list's are two. An edit made on the team is not in the list:
  exchange that Pokémon away and choose it again, and it comes back as the list has it.
- Edit POKéMON needs the team's menu, which under rules that want a full team (the Poké
  Cup, for one) only comes up once six are chosen. Under Anything Goes, Start brings it
  up from the first.
- Outside the editor the game labels Hidden Power as Normal, as the original does.
- Moves are checked one at a time. Combinations that cannot exist on one Pokémon in the
  Game Boy games are not rejected.
- OU Rules is on the list of your own rule sets, which has eight places: with eight
  rule sets of your own it is not offered. The six rule sets Free Battle starts with
  fill their panel, so there is nowhere else for it.
- OU Rules has the three move clauses and no others. Like Anything Goes it lets a
  species be on a team twice, and an item; the sleep and freeze clause and the rule on
  the last Pokémon are the game's own, in every battle.
- The clauses are held to where a team is chosen, for both sides, the computer's team
  being chosen there too. Nothing checks a battle: there is no other way for such a
  move to get onto a team.
- A rule set's clauses are in a byte of its saved form that the original game leaves
  empty. The original shows such a rule set without them, and saving the rules there
  loses them.
- The clauses under a rule set of your own have not been tried on a Game Pak's Pokémon,
  which is all such a rule set takes: there is no Game Pak in the tests. Nor, for the
  same reason, has a registered team with Mewtwo or the like on it been tried under
  OU Rules, no rental being one of the five.
- The original trainer's name and ID stay as the rental has them.
- Change Trainer has only been tried in Free Battle. A typed name shows there; the other
  modes name the player in code this does not change.
- A chosen trainer keeps the one face you gave them: it does not change with how the
  battle went, as the game's own trainers' faces do. Which face a trainer starts on in
  the window was picked by eye, to be the one they would meet you with.
- Only rentals get EDIT, not Pokémon read from a Game Pak. On a team that has both, A on
  one of the others after Edit POKéMON does nothing but sound the error; that has not
  been tried, there being no Game Pak in the tests.
- USA version only.

## What has been tested

Everything below was run in BizHawk 2.x with its Ares64 core, driven by scripts. Most of
it is now an automated suite (`mod/tests/emu`, 59 scenarios) that plays the editor and
checks the game's memory afterwards; see "Tests" in [NOTES.md](NOTES.md).

- Moves, level, happiness, DVs and Stat Exp edited and carried into a battle.
- Shiny, gender, Unown's letter and Hidden Power shown and updated as DVs change.
- Nicknames typed across both pages, special signs included; one shown in battle and
  read back byte for byte from a registered team after a console reset. The ten-character
  limit, an empty name, backing out, and the cursor wrapping at every edge.
- A registered team reloaded after a console reset with its edits intact.
- A rental edited on the team, by Edit POKéMON and by EDIT under EXCHANGE: the edits made
  before it was entered kept and added to, and all of it carried into a battle; the
  second of two edited with the first untouched; the computer's team; a second player's,
  with controller 2. Under Poké Cup rules, the level of one of the team held to 50–55 and
  stopped at the team's level total.
- Change Trainer: every face of every trainer in the window, and a chosen picture, name
  and title where the two sides are set against each other, on the order screen and on
  the result after a battle; a name taken back; a name still there on the next visit to
  the entry screen; a second player choosing theirs with controller 2; the computer's
  picture, name and title never changing; all of it gone after a power cycle.
- The ITEM list holding all 42 items, and one from beyond the original six (Leftovers)
  entered with a rental.
- EDIT from Free Battle and from Register POKéMON.
- OU Rules: on Free Battle's list and in "Check Rules"; a rental refused for Fissure,
  with Yes and the move greyed out and the cursor kept off Yes, and entered once the
  move is edited away; Baton Pass and Spider Web each left out of the list of moves
  beside the other, and a Pokémon with both refused; a registered team with Fissure on
  it refused under OU Rules and chosen under Anything Goes; a battle begun under it;
  and Anything Goes refusing nothing.
- RULE EDIT: the three questions answered both ways, a rule set kept with two clauses,
  and the same rule set on Free Battle's list with them after a power cycle.
- Under Poké Cup rules the level stops at 50 and 55.
- A second player editing with controller 2, with controller 1 ignored meanwhile.
- A build made to believe the console has 4 MB of RAM (`tools/mod/make_4mb_rom.py`): the
  entry screen keeps 120 KB of its memory pool free with the mod loaded, and the editor
  and keyboard allocate nothing; a chosen face is then shown where the two sides are set
  against each other and on the order screen. OU Rules, "Check Rules" and RULE EDIT on
  that build too. (A battle on that build was run before
  the keyboard was added; the mod is unloaded by then.)
- The original ROM still builds byte for byte from the same tree, and the patch applied
  to it reproduces the modified ROM.

This build has also been run on a real Nintendo 64, by hand; the checks listed above
are the emulator's.

Not tested: standalone ares, other emulators, the Stadium cups and Gym Leader Castle
(they use the same entry screen), and the Japanese version.

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
7. Up to the name, A. Type a name using both cases and a sign from the bottom row, then
   Start, A. The lower panel shows the new name.
8. B, then Yes. The party box shows the Pokémon; Start, then **Change Trainer**. Right
   to another trainer, C Right for another of their faces, A. The menu comes back; OK.
9. Pick the opponent's team and start the battle. The face you chose should be beside
   your team before the battle and on the screen where you put it in order. Check the
   name, moves and HP in battle.
10. Leave and come back to the picker a few times, including after a battle.
11. Two players: Free Battle → 1P vs 2P. Player 2 edits with controller 2.
12. Start → **OK to Register**, switch the console off and on, and load the team from
    Registered POKéMON.
13. Free Battle → 1P vs COM → **Edit Rules** → **OU Rules**. R shows its rules, the last
    line being "Moves that cannot be known". Then Rental Only: DIGLETT, the first of
    the tenth row, opens with Yes and FISSURE greyed out. EDIT, change Fissure, B: Yes is back.
14. OPTIONS → **RULE EDIT** → Make rules. The page has three questions about moves above
    OK. Answer one "Don't use", OK, leave and save. The rule set should be in Free
    Battle's list, with "Moves that cannot be known" under R.
15. Repeat steps 3–9 and 13 with the Expansion Pak removed (or fitted, whichever you did
    not start with).

If something goes wrong, the useful details are the step, whether the Expansion Pak was
fitted, the flashcart and its firmware, and what was on screen: a freeze on entering the
picker points at loading the mod, a freeze on opening the Yes / No menu at the hooks,
leftover graphics after closing the editor at the redraw, and a wrong or missing trainer
picture before a battle at the pictures' new directory. A freeze on Free Battle's first
screen, on "Check Rules" or on entering RULE EDIT points at loading the mod there.

## Building

See "Building" in [NOTES.md](NOTES.md). In short, inside WSL:

    python3 tools/mod/check_rom.py <path-to-rom>   # verify the ROM and install it as the base
    tools/mod/wsl_build.sh init                    # first time only
    tools/mod/wsl_build.sh mod                     # build/stadium2-rental-editor-us.bps

The build ends by comparing its output with `mod/checksums.txt`, which holds the SHA-1 of
the patch and of the ROM it produces. A patch you were given can be checked against the
same file.

The mod leaves the decompilation's sources untouched. Its code is one new overlay stored
in an unused part of the ROM, and eight functions of the entry screen are replaced by
jumps into it. Six more, on the screen that introduces a battle and shows its result,
have a few instructions changed in place so that they use the chosen trainer picture,
name and title. The trainer pictures get a second directory, in another unused part of
the ROM, that gives each face a number of its own; no picture is moved or changed.
[NOTES.md](NOTES.md) has the details.

This is built on [michiiik/pokestadiumgs](https://github.com/michiiik/pokestadiumgs), a
fork of [pret/pokestadiumgs](https://github.com/pret/pokestadiumgs). Move legality comes
from Pokémon Showdown's Gen 2 learnsets and the pret Gold and Crystal disassemblies.
