#ifndef MOD_CLAUSES_H
#define MOD_CLAUSES_H

#include "game.h"

/*
 * Move clauses: rules about the moves a Pokemon may know, which the stock game has no
 * way to state. A rule set carries them in the low bits of its flag word. The game's
 * own rule sets have every bit of the lower half clear and nothing reads them, and a
 * player's own rules are made from nothing, so a rule set without the mod's bits is
 * one without clauses.
 *
 * They are held to where a team is chosen: the editor does not offer a move a clause
 * rules out, a Pokemon that breaks one cannot be entered, and a registered team with
 * one on it cannot be chosen.
 */
#define CLAUSE_EVASION 0x1   /* no Double Team or Minimize */
#define CLAUSE_OHKO 0x2      /* no Fissure, Guillotine or Horn Drill */
#define CLAUSE_TRAP_PASS 0x4 /* no Baton Pass together with Mean Look or Spider Web */
#define CLAUSE_MASK 0x7

/* clauses.c */
s32 Clauses_Of(Rules *rules);
s32 Clauses_MoveRefused(Rules *rules, Pokemon *mon, s32 move, s32 slot);
s32 Clauses_Broken(Rules *rules, Pokemon *mon);
void Clauses_Describe(s32 clauses, char *title, char *description);
s32 Clauses_RefusesRow(Menu *menu, s32 row);

/* rules.c */
Rules *Rules_InForce(void);
void Rules_UseChosen(void);

#endif
