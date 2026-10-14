#include "clauses.h"
#include "edit.h"

#include "clause_moves.inc.c"

/* The rule viewer's line for the clauses, worded as the game words its own: a rule set
 * with any of them has the one line, and what it says behind it is a sentence for each. */
static char sTitle[] = "Moves that cannot be known";
static char sEvasion[] = "No POK\xE9MON may know DOUBLE TEAM or MINIMIZE.";
static char sOhko[] = "No POK\xE9MON may know FISSURE, GUILLOTINE or HORN DRILL.";
static char sTrapPass[] = "No POK\xE9MON may know BATON PASS together with MEAN LOOK\nor SPIDER WEB.";

static s32 Clauses_Listed(const u8 *moves, s32 count, s32 move) {
    s32 i;

    for (i = 0; i < count; i++) {
        if (moves[i] == move) {
            return TRUE;
        }
    }
    return FALSE;
}

static s32 Clauses_KnowsAny(Pokemon *mon, const u8 *moves, s32 count, s32 exceptSlot) {
    s32 i;

    for (i = 0; i < count; i++) {
        if (Edit_Knows(mon, moves[i], exceptSlot)) {
            return TRUE;
        }
    }
    return FALSE;
}

/* The clauses a rule set has. */
s32 Clauses_Of(Rules *rules) {
    return rules != NULL ? rules->flags & CLAUSE_MASK : 0;
}

/* Whether the rules keep a Pokemon from knowing `move` in `slot`, given its other moves. */
s32 Clauses_MoveRefused(Rules *rules, Pokemon *mon, s32 move, s32 slot) {
    s32 clauses = Clauses_Of(rules);

    if (move == 0) {
        return FALSE;
    }
    if ((clauses & CLAUSE_EVASION) && Clauses_Listed(sEvasionMoves, sizeof(sEvasionMoves), move)) {
        return TRUE;
    }
    if ((clauses & CLAUSE_OHKO) && Clauses_Listed(sOhkoMoves, sizeof(sOhkoMoves), move)) {
        return TRUE;
    }
    if (clauses & CLAUSE_TRAP_PASS) {
        if (move == MOVE_BATON_PASS) {
            return Clauses_KnowsAny(mon, sTrappingMoves, sizeof(sTrappingMoves), slot);
        }
        if (Clauses_Listed(sTrappingMoves, sizeof(sTrappingMoves), move)) {
            return Edit_Knows(mon, MOVE_BATON_PASS, slot);
        }
    }
    return FALSE;
}

/* Whether a Pokemon knows a move the rules keep it from knowing. */
s32 Clauses_Broken(Rules *rules, Pokemon *mon) {
    s32 slot;

    if (Clauses_Of(rules) == 0 || mon == NULL) {
        return FALSE;
    }
    for (slot = 0; slot < MAX_MOVES; slot++) {
        if (Clauses_MoveRefused(rules, mon, mon->moves[slot], slot)) {
            return TRUE;
        }
    }
    return FALSE;
}

static char *Clauses_Append(char *end, char *sentence, char *start) {
    if (end != start) {
        *end++ = '\n';
    }
    HAL_Strcpy(end, sentence);
    while (*end != '\0') {
        end++;
    }
    return end;
}

/* The rule viewer's line for a rule set with these clauses. */
void Clauses_Describe(s32 clauses, char *title, char *description) {
    char *end = description;

    HAL_Strcpy(title, sTitle);
    *end = '\0';
    if (clauses & CLAUSE_EVASION) {
        end = Clauses_Append(end, sEvasion, description);
    }
    if (clauses & CLAUSE_OHKO) {
        end = Clauses_Append(end, sOhko, description);
    }
    if (clauses & CLAUSE_TRAP_PASS) {
        end = Clauses_Append(end, sTrapPass, description);
    }
}

/* --- A registered team ---
 *
 * The ENTER menu lets no Pokemon onto a team that breaks a clause, and the editor gives
 * none a move that does. But a registered team is entered whole, from the menu its list
 * gives the one chosen: OK / Select again / Check. The game has nothing to hold such a
 * team against, since it keeps the teams of each kind of rules apart; the mod's rule
 * set shares Anything Goes's. So under rules with clauses that OK is greyed out and
 * refused, as the ENTER menu's "Yes" is, for a team with a Pokemon on it that could
 * not have been entered: one the rules keep out, or one that breaks a clause.
 */

static s32 Clauses_TeamRefused(Rules *rules, u8 *party) {
    ListCell *cell = (ListCell *)(party + PARTY_CELLS);
    s32 i;

    for (i = 0; i < PARTY_SIZE; i++, cell++) {
        if (cell->pokemon.species != 0 &&
            (!Rules_Admit(rules, &cell->pokemon) || Clauses_Broken(rules, &cell->pokemon))) {
            return TRUE;
        }
    }
    return FALSE;
}

/* Whether `row` of a popup menu is the OK for a registered team that the rules refuse. */
s32 Clauses_RefusesRow(Menu *menu, s32 row) {
    Rules *rules = Rules_InForce();
    MenuDef *def = menu->def;
    u8 *sets;

    if (Clauses_Of(rules) == 0 || def == NULL || row < 0 || def->textBank != ENTRY_TEXT_BANK ||
        def->entries[row].text != ENTRY_TEXT_SET_OK) {
        return FALSE;
    }
    sets = (u8 *)menu - ENTRY_STATE_MENU + ENTRY_STATE_LIST;
    return Clauses_TeamRefused(rules, RegisteredSets_Chosen(sets));
}
