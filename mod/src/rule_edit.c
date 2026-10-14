#include "clauses.h"

/*
 * The move clauses in the rule editor (RULE EDIT, under OPTIONS), where a player makes
 * rule sets of their own.
 *
 * Its page for one rule set is a column of rows, each a question with its answer at the
 * right: the name, who qualifies, the levels and their total, "Use items?" and "Hold
 * identical items?", and OK at the foot. The clauses are three more questions between
 * the last of those and OK, asked and answered in the game's words: what a clause keeps
 * out is "used" or not, as items are.
 *
 * The page is the game's, drawn and run by code that knows its seven rows by number, so
 * the mod's rows take the numbers after "Hold identical items?" and OK the one after
 * them. The game's drawing gives up its own OK and the hand that points at it
 * (mod/stock_patches.txt), and the mod draws its three rows, OK, and the hand on any of
 * the four; the rows' input is the mod's, which hands OK and the game's own rows on.
 *
 * Three more rows do not fit the page's window, which the game's seven fill, so the
 * window is made higher: as high as the window of Pokemon that opens over it for "who
 * qualifies", and no higher, or it would show from under that one. That leaves the
 * mod's rows 28 apart where the game's are 30.
 */

#define ROW_HELD_ITEMS 5 /* "Hold identical items?", which is skipped while items are not used */
#define ROW_CLAUSES 6
#define NUM_CLAUSE_ROWS 3
#define ROW_OK (ROW_CLAUSES + NUM_CLAUSE_ROWS)
#define STOCK_ROW_OK 6 /* what the game's own code knows OK as */

/* Where the page puts things, from its drawing (func_82D03CC0): a question, its answer
 * ending at the right, and the hand before the question, 2 higher. "Hold identical
 * items?" is 0xD4 down the page, and the mod's rows follow it. */
#define QUESTION_X 0x3A
#define ANSWER_X 0x1DA
#define POINTER_X 0x12
#define POINTER_RISE 2
#define ROW_SPACING 28
#define CLAUSES_Y (0xD4 + ROW_SPACING)
#define PAGE_FONT 8

#define SOUND_TOGGLE 0x12 /* as "Use items?" sounds when it is answered */

static char sEvasion[] = "Use evasion moves?";
static char sOhko[] = "Use one-hit KO moves?";
static char sTrapPass[] = "Use BATON PASS with trapping?";

static char *RuleEdit_Question(s32 clause) {
    if (clause == 0) {
        return sEvasion;
    }
    return clause == 1 ? sOhko : sTrapPass;
}

/**
 * Runs in place of func_82D0034C, which reads the player's rule sets from the save file
 * as the rule editor starts, and is where the mod is loaded for it. The page's window
 * is made higher before anything is shown.
 */
void Mod_RuleEditSetup(void) {
    s16 *window = RuleEdit_PageWindow();

    window[1] = RULE_EDIT_WINDOW_Y;
    window[3] = RULE_EDIT_WINDOW_HEIGHT;
    orig_func_82D0034C();
}

/**
 * Replaces func_82D00BB4, the page's input: the cursor up and down its rows, A to answer
 * the one it is on, and B for OK. A on a clause's row turns the clause on or off; the
 * game's own rows and OK go to the game's code for them.
 */
void Mod_RuleEditInput(void) {
    u8 *page = RuleEdit_GetPage();
    Rules *rules = (Rules *)(page + RULE_EDIT_RULES);
    s8 *cursor = (s8 *)(page + RULE_EDIT_CURSOR);
    s32 pressed = gRuleEditPressed;
    s32 row;

    RuleEdit_MoveCursor(cursor, 0, ROW_OK, (rules->flags & RULES_HELD_ITEMS) ? 0xFF : ROW_HELD_ITEMS);
    if (!(pressed & BTN_A)) {
        if (!(pressed & BTN_B)) {
            return;
        }
        *cursor = ROW_OK;
    }
    row = *cursor;
    if (row >= ROW_CLAUSES && row < ROW_OK) {
        rules->flags ^= 1 << (row - ROW_CLAUSES);
        Sound_Play(SOUND_TOGGLE);
        return;
    }
    if (row == ROW_OK) {
        *cursor = STOCK_ROW_OK;
    }
    RuleEdit_Choose();
}

static void RuleEdit_SetColor(s32 chosen, s32 alpha) {
    if (chosen) {
        Text_SetColor(0xFF, 0xFF, 0, 0xFF);
    } else {
        Text_SetColor(0xFF, 0xFF, 0xFF, alpha);
    }
}

/**
 * Runs in place of func_82D03CC0, which draws the rule editor's lists and its page for
 * one rule set. The page gets the clauses' rows and its OK. They are dimmed with the
 * rest while the levels are being set.
 */
void Mod_RuleEditDraw(u8 *widget) {
    u8 *page = *(u8 **)(widget + RULE_WIDGET_PAGE);
    Rules *rules = (Rules *)(page + RULE_EDIT_RULES);
    s32 mode;
    s32 cursor;
    s32 alpha;
    s32 x;
    s32 y;
    s32 i;
    s32 row;

    orig_func_82D03CC0(widget);
    mode = page[RULE_EDIT_MODE];
    if (widget[RULE_WIDGET_MOVING] != 0 || (mode != RULE_EDIT_ROWS && mode < RULE_EDIT_SHOWN)) {
        return;
    }
    cursor = *(s8 *)(page + RULE_EDIT_CURSOR);
    alpha = mode >= RULE_EDIT_DIMMED ? 0x80 : 0xFF;
    x = *(s16 *)(widget + RULE_WIDGET_X);
    y = *(s16 *)(widget + RULE_WIDGET_Y) + CLAUSES_Y;

    Text_Begin();
    Text_SetFont(PAGE_FONT, 1);
    for (i = 0; i < NUM_CLAUSE_ROWS; i++) {
        RuleEdit_SetColor(cursor == ROW_CLAUSES + i, alpha);
        Text_DrawFrom(x + QUESTION_X, y + ROW_SPACING * i, TEXT_FROM_LEFT, RuleEdit_Question(i));
        Text_DrawFrom(x + ANSWER_X, y + ROW_SPACING * i, TEXT_FROM_RIGHT,
                      Text_Lookup(RULE_EDIT_TEXT_BANK,
                                  (rules->flags & (1 << i)) ? RULE_EDIT_TEXT_DONT_USE : RULE_EDIT_TEXT_USE));
    }
    RuleEdit_SetColor(cursor == ROW_OK, alpha);
    Text_DrawFrom(x + QUESTION_X, y + ROW_SPACING * NUM_CLAUSE_ROWS, TEXT_FROM_LEFT,
                  Text_Lookup(RULE_EDIT_TEXT_BANK, RULE_EDIT_TEXT_OK));
    Text_End();

    /* The game has the hand only while the cursor is on the rows, and so here. */
    row = cursor - ROW_CLAUSES;
    if (mode == RULE_EDIT_ROWS && row >= 0) {
        RuleEdit_DrawPointer(x + POINTER_X, y + ROW_SPACING * row - POINTER_RISE);
    }
}
