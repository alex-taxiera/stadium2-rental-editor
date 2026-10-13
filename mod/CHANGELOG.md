# Changelog

What changed in each release of the patch, newest first. A release's heading is its tag,
and the text under it is published as the release's notes; see "Releases" in
[NOTES.md](NOTES.md).

## v0.4.0

Change Trainer now has every face of every trainer, where it had one each.

- **Faces.** Most of the game's trainers have two or three pictures: pleased, upset,
  composed. In the trainer window C Left and C Right go round them, wherever the cursor
  is, and the line under the window shows the two buttons and "Face" whenever the
  trainer has more than one. That makes 158 pictures to choose from, where there were
  67.
- **A better first face.** Stepping to a trainer used to show their first picture, which
  for most is the upset one. Each now starts on the face they would meet you with.
- Left and Right still step through the trainers, and the name and the title are as
  they were.

Things to know:

- The face you choose is the one you keep, whoever wins: it does not change after a
  battle, as the game's own trainers' faces do.
- As before, a picture, name and title last until the console is switched off, and
  Change Trainer has only been tried in Free Battle.
- Nothing else is changed, and only rentals can be edited.

Tested in BizHawk with its Ares64 core, with and without an Expansion Pak, and this
release has been run on a real Nintendo 64.

## v0.3.0

The editor and the trainer window now show the game's own pictures of the buttons, in
the places the game itself puts them, where they used to list keys in words.

- **On the keyboard**, the three wide keys each show the button that does the same from
  anywhere: R before `lower` / `UPPER`, B before `DEL`, START before `END`. The keyboard
  for a trainer's name has them too, which had no hints at all before.
- **In the editor**, the box beside the Pokémon says B "to quit", as the game's ITEM list
  does, and L "to min", R "to max" while a number is being changed. It no longer lists A
  and the Control Pad, which the cursor speaks for, and it is a smaller box.
- **In the trainer window**, an arrow either side of the picture's number or of the title
  shows that Left and Right step through them, and one line under them has A and B.

Things to know:

- No button does anything it did not do before.
- Two shortcuts are no longer mentioned on screen: Left and Right take a bigger step on a
  number, and turn a page of the move list. The guide has every button in a table.
- Only rentals can be edited, as before.

Tested in BizHawk with its Ares64 core only, with and without an Expansion Pak. This
release has not been run on a console.

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
