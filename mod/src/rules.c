#include "clauses.h"

#include "rule_ou.inc.c"

/*
 * The mod's own rule set, and what it takes to offer it.
 *
 * Free Battle's six rule sets fill their panel, and the sixth, "Edit Rules", opens the
 * list of the player's own. The mod's rule set goes on that list, after the player's.
 *
 * It is not a rule set of the player's kind, though. Those are for battles of three
 * out of six Pokemon from a Game Pak, and say so to the session, which gives them a
 * mode of their own, no rentals and no registered teams. The mod's is Anything Goes
 * in all of that, so it has Anything Goes's kind, and the session then knows no more
 * than that kind: it looks the game's own record up again wherever it wants the
 * rules. So the choice is noted where it outlasts the screen, and the entry screen,
 * the one place that decides who may enter, is given the mod's record instead. A
 * battle has Anything Goes's rules, which differ in nothing a battle looks at.
 */

/* The rule set in force on the entry screen. */
Rules *Rules_InForce(void) {
    return *(Rules **)(gEntrySettings + ENTRY_SETTINGS_RULES);
}

/**
 * Runs in place of func_83101C80, which sets Free Battle's rule select up and reads the
 * player's own rules from the save file. Adds the mod's rule set to those, if eight
 * are not there already.
 */
void Mod_RuleSelectSetup(u8 *state, void *ctx, u8 *settings) {
    s32 count;

    orig_func_83101C80(state, ctx, settings);
    *gChosenRules = 0;
    count = state[RULE_SELECT_SAVED_COUNT];
    if (count < RULE_SELECT_SAVED_MAX) {
        *(Rules *)(state + RULE_SELECT_SAVED + count * sizeof(Rules)) = sOuRules;
        state[RULE_SELECT_SAVED_COUNT] = count + 1;
    }
}

/**
 * Runs in place of func_8310065C, which ends the rule select by filling in what was
 * chosen, or that nothing was. Notes whether the rule set was the mod's: the one
 * record of Anything Goes's kind with clauses.
 */
void Mod_RuleSelectDone(u8 *state, s32 cancelled) {
    Rules *chosen;

    orig_func_8310065C(state, cancelled);
    chosen = (Rules *)(*(u8 **)(state + RULE_SELECT_SETTINGS) + RULE_SETTINGS_RULES);
    *gChosenRules = !cancelled && chosen->kind == RULES_ANYTHING_GOES && Clauses_Of(chosen) != 0 ? CHOSEN_OU : 0;
}

/**
 * Stands in for func_8004C874, the look-up of a text, where the list of registered teams
 * heads itself "Registered POKeMON / " and the rule set's name (mod/asm_patches.txt).
 * The game names its own rule sets by a text each; one with a name in its record has no
 * text, and the screen's other headings know to show the record's name then. This one
 * does not, a player's own rules having no registered teams.
 */
char *Mod_RuleName(s32 bank, s32 text) {
    return text < 0 ? Rules_InForce()->name : Text_Lookup(bank, text);
}

/* As the entry screen starts: gives it the mod's rule set if that was chosen for this
 * Free Battle. The record is kept in the session, in the room for a player's own rules,
 * which Anything Goes leaves empty: the screen's settings outlast the mod. */
void Rules_UseChosen(void) {
    u8 *settings = gEntrySettings;
    Rules **rules = (Rules **)(settings + ENTRY_SETTINGS_RULES);
    Rules *own;

    if (*gChosenRules != CHOSEN_OU || (*(u16 *)(settings + ENTRY_SETTINGS_MODE) & 0xFF00) != MODE_FREE_BATTLE ||
        *rules == NULL || (*rules)->kind != RULES_ANYTHING_GOES) {
        return;
    }
    own = (Rules *)(gSession + SESSION_RULES);
    *own = sOuRules;
    *rules = own;
}

/* The rule set the viewer shows, as it is given to the viewer's heading. */
static Rules sViewedRules;

/**
 * Runs in place of func_82C04350, which makes the rule viewer's lines for a rule set.
 * A rule set with move clauses gets a line for them, if the ten there is room for are
 * not all taken.
 *
 * The viewer goes on to head the list with the rule set's name, which it has by kind:
 * a text of its own for each kind of the game's, and for a player's rules the name in
 * the record. The mod's rule set has a name in its record and Anything Goes's kind,
 * so from here on the viewer is shown a copy of it that says it is a player's. The
 * copy is in this copy of the mod, which is in memory for as long as the viewer is.
 */
void Mod_RuleViewerLines(void) {
    u8 *state = RuleViewer_GetState();
    Rules **shown = (Rules **)(state + RULE_VIEWER_RULES);
    Rules *rules;
    s32 clauses;
    s32 count;
    RuleLine *line;

    orig_func_82C04350();
    rules = *shown;
    clauses = Clauses_Of(rules);
    count = state[RULE_VIEWER_COUNT];
    if (clauses != 0 && count < RULE_VIEWER_MAX_LINES) {
        line = (RuleLine *)(state + RULE_VIEWER_LINES) + count;
        line->kind = 0;
        Clauses_Describe(clauses, line->title, line->description);
        state[RULE_VIEWER_COUNT] = count + 1;
    }
    if (rules != NULL && rules->kind != RULES_CUSTOM && rules->nameText < 0 && rules->name[0] != '\0') {
        sViewedRules = *rules;
        sViewedRules.kind = RULES_CUSTOM;
        *shown = &sViewedRules;
    }
}
