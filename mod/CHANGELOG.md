# Changelog

What changed in each release of the patch, newest first. A release's heading is its tag,
and the text under it is published as the release's notes; see "Releases" in
[NOTES.md](NOTES.md).

## v0.2.0

A rental that is already on your team can now be edited where it is, and you can choose
your own trainer picture, name and title.

- **Edit POKéMON**, a new entry on the menu a chosen team gets on Start. The cursor goes
  to the team's box: A on a rental opens the editor on it, B closes it for the next one.
  Nothing has to be taken off the team and chosen again, and everything changed before
  the Pokémon was entered is still there. The game's own Reselect some POKéMON leads to
  the same editor: its EXCHANGE menu has **EDIT** under Yes / No.
- **Change Trainer**, on the same menu: any of the game's 67 trainer pictures, a name of
  up to seven characters in place of 1P, and one of the game's forty titles in place of
  POKéMON TRAINER. They are yours on the screens before and after each battle until the
  console is switched off, and each player chooses their own.
- **Happiness** is a field in the editor, beside the level. It decides the power of
  Return and Frustration, which the editor shows as you change it.
- **Held items**: the game's ITEM list now has every item worth holding in a battle, 42
  of them, where the original offers six berries plus whatever a Game Pak owns.
- The editor marks the field you are on with the game's own brackets, and the move list
  has the game's scroll bar and pointing hand.

Things to know:

- Under rules that want a full team, such as the Poké Cup, the team's menu only comes up
  once six are chosen, so Edit POKéMON is not there before that. Under Anything Goes,
  Start brings it up from the first Pokémon.
- The level of a Pokémon on the team stops where the team would go past the rules' level
  total, because the game's answer to that is to have you choose the last Pokémon again.
- A trainer's name shows in Free Battle, the only mode Change Trainer has been tried in.
- Only rentals can be edited, as before.

An earlier build of the patch has been run on a real Nintendo 64. This release itself has
been tested in BizHawk with its Ares64 core only.

## v0.1.0

First release. Adds an **EDIT** entry to the menu shown when you pick a rental Pokémon in
Pokémon Stadium 2 (USA). It opens an editor for that rental, limited to what the Game Boy
games allow, and the edited Pokémon is what enters the battle or the registered team.

- **Moves**: any move the species or an earlier evolution learns in Red, Blue, Yellow,
  Gold, Silver or Crystal by level, TM/HM, tutor or breeding.
- **Level**, within the range of the rules in force.
- **DVs** and **Stat Exp**, with the stats recalculated as you change them. The editor
  shows what the DVs decide besides stats: gender, shininess, Unown's letter and Hidden
  Power's type and power.
- **Nickname**, typed on a keyboard laid out like the Game Boy's.
- Works in Free Battle and when registering a team, for either player, with or without
  an Expansion Pak. Registered teams keep their edits.

Tested in BizHawk with its Ares64 core only. It has not been run on a console yet.
