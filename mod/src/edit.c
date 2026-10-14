#include "clauses.h"
#include "edit.h"

#include "legal_moves.inc.c"

#define REPEAT_DELAY 16
#define REPEAT_RATE 3

/* Stat Exp only matters through floor(ceil(sqrt(exp)) / 4), which runs from 0 to 63.
 * The editor steps between those tiers so every press changes the stat. */
#define MAX_STAT_EXP_TIER 63
#define STAT_EXP_BIG_STEP 8
#define DV_BIG_STEP 4
#define LEVEL_BIG_STEP 10
#define HAPPINESS_BIG_STEP 25 /* ten points of Return's or Frustration's power */

/* The stock panel waits this long before loading a model, so the editor does too. */
#define MODEL_RELOAD_DELAY 2

static s32 Edit_IsLegal(s32 species, s32 move) {
    return (sLegalMoves[species][move >> 3] >> (move & 7)) & 1;
}

s32 Edit_MoveCount(Pokemon *mon) {
    s32 count = 0;

    while (count < MAX_MOVES && mon->moves[count] != 0) {
        count++;
    }
    return count;
}

/* Move rows on offer: one per move, plus an empty one while there is room. */
s32 Edit_SlotCount(Pokemon *mon) {
    s32 count = Edit_MoveCount(mon);

    return count < MAX_MOVES ? count + 1 : MAX_MOVES;
}

s32 Edit_Knows(Pokemon *mon, s32 move, s32 exceptSlot) {
    s32 i;

    for (i = 0; i < MAX_MOVES; i++) {
        if (i != exceptSlot && mon->moves[i] == move) {
            return TRUE;
        }
    }
    return FALSE;
}

/* The HP DV is not stored: it is the low bit of each of the other four. */
s32 Edit_HpDv(Pokemon *mon) {
    s32 dvs = mon->dvs;

    return (((dvs >> 12) & 1) << 3) | (((dvs >> 8) & 1) << 2) | (((dvs >> 4) & 1) << 1) | (dvs & 1);
}

/* Rows 1-4 are Attack, Defense, Speed and Special, packed high nibble first. */
s32 Edit_GetDv(Pokemon *mon, s32 row) {
    if (row == ROW_HP) {
        return Edit_HpDv(mon);
    }
    return (mon->dvs >> ((NUM_ROWS - 1 - row) * 4)) & 0xF;
}

static void Edit_SetDv(Pokemon *mon, s32 row, s32 value) {
    s32 shift = (NUM_ROWS - 1 - row) * 4;

    mon->dvs = (mon->dvs & ~(0xF << shift)) | (value << shift);
}

/* Hidden Power is one of the sixteen types from Fighting to Dark: two bits each from
 * the Attack and Defense DVs. */
static s32 Edit_HiddenPowerType(Pokemon *mon) {
    s32 type = (((mon->dvs >> 12) & 3) << 2) | ((mon->dvs >> 8) & 3);

    type++;
    if (type >= TYPE_BIRD) {
        type++;
    }
    if (type >= TYPE_PHYSICAL_END) {
        type += TYPE_FIRE - TYPE_PHYSICAL_END;
    }
    return type;
}

/* Its power, 31 to 70, comes from the top bit of each DV and the low bits of Special. */
static s32 Edit_HiddenPowerPower(Pokemon *mon) {
    s32 dvs = mon->dvs;
    s32 topBits = (((dvs >> 15) & 1) << 3) | (((dvs >> 11) & 1) << 2) | (((dvs >> 7) & 1) << 1) | ((dvs >> 3) & 1);

    return (5 * topBits + (dvs & 3)) / 2 + 31;
}

/* A move's type and power as this Pokemon would use it. Return grows with happiness
 * and Frustration with the lack of it, each up to 102. */
s32 Edit_MoveType(Pokemon *mon, s32 move) {
    return move == MOVE_HIDDEN_POWER ? Edit_HiddenPowerType(mon) : Move_Type(move);
}

s32 Edit_MovePower(Pokemon *mon, s32 move) {
    if (move == MOVE_RETURN) {
        return mon->happiness * 10 / 25;
    }
    if (move == MOVE_FRUSTRATION) {
        return (MAX_HAPPINESS - mon->happiness) * 10 / 25;
    }
    return move == MOVE_HIDDEN_POWER ? Edit_HiddenPowerPower(mon) : Move_Power(move);
}

/* Everything the DVs change about how the Pokemon looks. */
static s32 Edit_Look(Pokemon *mon) {
    s32 look = Pokemon_IsShiny(mon->dvs);

    if (mon->species == SPECIES_UNOWN) {
        look |= Unown_Letter(mon->dvs) << 1;
    } else if (mon->species == SPECIES_SMEARGLE) {
        look |= Smeargle_Paint(mon->dvs) << 1;
    }
    return look;
}

/* The model beside the panel and the icon in the list are made when a record is first
 * shown, so both have to be asked for again. */
void Edit_ReloadLook(DetailPanel *panel) {
    Pokemon *mon = panel->pokemon;

    panel->modelTimer = MODEL_RELOAD_DELAY;
    Icon_Load(((ListCell *)mon)->icon, 0, mon);
}

static s32 Edit_StatExpForTier(s32 tier) {
    if (tier <= 0) {
        return 0;
    }
    if (tier >= MAX_STAT_EXP_TIER) {
        return MAX_STAT_EXP;
    }
    return (4 * tier - 1) * (4 * tier - 1) + 1;
}

static s32 Edit_MinLevel(void) {
    s32 level = Rules_InForce()->minLevel;

    return level < MIN_LEVEL ? MIN_LEVEL : level;
}

static s32 Edit_MaxLevel(void) {
    s32 level = Rules_InForce()->maxLevel;

    if (level > 100) {
        level = 100;
    }
    return level < MIN_LEVEL ? MIN_LEVEL : level;
}

/* Whether the team is past the rules' limit on its levels together. Only for a panel
 * opened on one of the team: that is the picker's own, the first thing in its state. */
static s32 Edit_TeamOverLevels(DetailPanel *panel) {
    return Party_LowestLevelTotal((u8 *)panel + ENTRY_STATE_PARTY) > Rules_InForce()->maxLevelTotal;
}

/* Gives the Pokemon a level and returns the one it got. For one of the team that is the
 * highest up to `level` that keeps the team within the limit, if it was within it: past
 * the limit the game would have the team's last Pokemon chosen again, edits and all. */
static s32 Edit_SetLevel(DetailPanel *panel, s32 level) {
    Pokemon *mon = panel->pokemon;
    s32 old = mon->level;
    u32 oldExp = mon->exp;
    s32 limited = panel->mode == PANEL_MODE_EXCHANGE && level > old && !Edit_TeamOverLevels(panel);

    for (;;) {
        mon->exp = Pokemon_ExpForLevel(mon->species, level);
        Pokemon_RecalcStats(mon);
        if (!limited || level == old || !Edit_TeamOverLevels(panel)) {
            break;
        }
        level--;
    }
    if (level == old) {
        mon->exp = oldExp;
        Sound_Play(SOUND_ERROR);
    }
    return level;
}

s32 Edit_CanEdit(DetailPanel *panel) {
    Pokemon *mon = panel->pokemon;

    /* A rental about to be entered, or one already on the team: the team's box holds
     * cells like the list's, so the editor works on either where it is. */
    return (panel->mode == PANEL_MODE_ENTER || panel->mode == PANEL_MODE_EXCHANGE) && mon != NULL &&
           (mon->flags & POKEMON_FLAG_RENTAL) && mon->species >= 1 && mon->species <= NUM_SPECIES;
}

s32 Edit_IsActive(DetailPanel *panel) {
    EditState *state = Edit_GetState();

    if (state->mode == EDIT_OFF || state->panel != panel) {
        return FALSE;
    }
    /* The panel was closed or reused behind our back. */
    if (panel->state != PANEL_MENU || !Edit_CanEdit(panel)) {
        state->mode = EDIT_OFF;
        return FALSE;
    }
    return TRUE;
}

void Edit_Open(DetailPanel *panel, s32 direct) {
    EditState *state = Edit_GetState();

    state->mode = EDIT_FIELDS;
    state->col = COL_MOVES;
    state->row = 0;
    state->onName = FALSE;
    state->repeatTimer = 0;
    state->bracketPhase = 0;
    state->panel = panel;
    state->direct = direct;
}

void Edit_SetPending(s32 pending) {
    Edit_GetState()->pending = pending;
}

/* Closes the panel on No, as B does on its menu. */
void Edit_ClosePanel(DetailPanel *panel) {
    panel->cursor = ENTER_MENU_NO;
    panel->state = PANEL_CLOSING;
    panel->opening = 1.0f;
}

/* Stats follow from level, DVs and Stat Exp; the detail panel only repaints when asked. */
static void Edit_Recalculate(DetailPanel *panel) {
    Pokemon *mon = panel->pokemon;

    Pokemon_RecalcStats(mon);
    mon->hp = mon->stats[0];
    panel->redraw = TRUE;
}

static s32 Edit_FieldValid(Pokemon *mon, s32 col, s32 row) {
    if (row < 0 || row >= NUM_ROWS) {
        return FALSE;
    }
    if (col == COL_MOVES) {
        return row == ROW_LEVEL || row < Edit_SlotCount(mon);
    }
    if (col == COL_HAPPINESS) {
        return row == ROW_LEVEL;
    }
    if (col == COL_DV) {
        return row != ROW_HP;
    }
    return TRUE;
}

/* Returns whether there was a field to move to. */
static s32 Edit_MoveField(EditState *state, Pokemon *mon, s32 colStep, s32 rowStep) {
    s32 col = state->col + colStep;
    s32 row = state->row + rowStep;
    s32 i;

    /* Happiness has the level's row and no other. Sideways on the rows above, the cursor
     * passes over its column; up from it leads to the moves. */
    if (col == COL_HAPPINESS && row != ROW_LEVEL) {
        if (rowStep != 0) {
            col = COL_MOVES;
        } else {
            col += colStep;
        }
    }
    if (col < 0 || col >= NUM_COLS) {
        return FALSE;
    }
    if (rowStep != 0) {
        /* Skip rows that hold nothing, such as unused move slots. */
        while (row >= 0 && row < NUM_ROWS && !Edit_FieldValid(mon, col, row)) {
            row += rowStep;
        }
    } else if (!Edit_FieldValid(mon, col, row)) {
        for (i = 1; i < NUM_ROWS; i++) {
            if (Edit_FieldValid(mon, col, row + i)) {
                row += i;
                break;
            }
            if (Edit_FieldValid(mon, col, row - i)) {
                row -= i;
                break;
            }
        }
    }
    if (!Edit_FieldValid(mon, col, row)) {
        return FALSE;
    }
    state->col = col;
    state->row = row;
    Sound_Play(SOUND_CURSOR);
    return TRUE;
}

/* Where the scroll bar's knob belongs for the rows now showing. */
static s32 Edit_ScrollTarget(EditState *state) {
    s32 range = state->count - EDIT_LIST_ROWS;

    return range > 0 ? state->top * SCROLL_UNITS / range : 0;
}

/* The knob does not jump with the list: each frame it covers half of what is left. */
static void Edit_GlideScroll(EditState *state) {
    s32 left = Edit_ScrollTarget(state) - state->scroll;

    state->scroll += left / 2 != 0 ? left / 2 : left;
}

/* Fills the list with every move the species may know, in alphabetical order, less
 * those the rules keep it from knowing in this slot beside its other moves. The first
 * entry removes the move when the Pokemon would still have one left. */
static void Edit_BuildList(EditState *state, Pokemon *mon) {
    s32 current = mon->moves[state->row];
    s32 count = 0;
    s32 i;

    state->cursor = 0;
    if (current != 0 && Edit_MoveCount(mon) > 1) {
        state->list[count++] = EDIT_REMOVE;
    }
    for (i = 0; i < NUM_MOVES; i++) {
        s32 move = sMoveOrder[i];

        if (Edit_IsLegal(mon->species, move) && !Clauses_MoveRefused(Rules_InForce(), mon, move, state->row)) {
            if (move == current) {
                state->cursor = count;
            }
            state->list[count++] = move;
        }
    }
    state->count = count;
    state->top = state->cursor - EDIT_LIST_ROWS / 2;
    if (state->top > count - EDIT_LIST_ROWS) {
        state->top = count - EDIT_LIST_ROWS;
    }
    if (state->top < 0) {
        state->top = 0;
    }
    state->scroll = Edit_ScrollTarget(state);
    state->pointerTimer = 0.0f;
}

static void Edit_RemoveMove(Pokemon *mon, s32 slot) {
    s32 i;

    for (i = slot; i < MAX_MOVES - 1; i++) {
        mon->moves[i] = mon->moves[i + 1];
        mon->pp[i] = mon->pp[i + 1];
    }
    mon->moves[MAX_MOVES - 1] = 0;
    mon->pp[MAX_MOVES - 1] = 0;
}

static void Edit_MoveListCursor(EditState *state, s32 delta) {
    s32 cursor = state->cursor + delta;

    if (cursor < 0) {
        cursor = 0;
    }
    if (cursor > state->count - 1) {
        cursor = state->count - 1;
    }
    if (cursor == state->cursor) {
        return;
    }
    state->cursor = cursor;
    if (cursor < state->top) {
        state->top = cursor;
    }
    if (cursor > state->top + EDIT_LIST_ROWS - 1) {
        state->top = cursor - (EDIT_LIST_ROWS - 1);
    }
    Sound_Play(SOUND_CURSOR);
}

/* The buttons to act on this frame: those just pressed, plus any of `repeating` held
 * long enough, so long lists, big numbers and the keyboard are quick. */
s32 Edit_RepeatedButtons(u8 *timer, Pad *pad, s32 repeating) {
    s32 buttons = pad->pressed;
    s32 held = pad->held & repeating;

    if (held == 0 || (pad->pressed & held)) {
        *timer = 0;
    } else if (++*timer >= REPEAT_DELAY) {
        *timer = REPEAT_DELAY - REPEAT_RATE;
        buttons |= held;
    }
    return buttons;
}

static void Edit_UpdateFields(EditState *state, Pad *pad, DetailPanel *panel) {
    Pokemon *mon = panel->pokemon;
    s32 buttons = pad->pressed;

    if (buttons & BTN_B) {
        Sound_Play(SOUND_CANCEL);
        state->mode = EDIT_OFF;
        if (state->direct) {
            /* There was no menu before the editor, so none after: back to the team. */
            Edit_ClosePanel(panel);
        } else if (panel->mode == PANEL_MODE_EXCHANGE) {
            /* Yes here would give the Pokemon up for another. */
            panel->cursor = ENTER_MENU_NO;
        } else {
            /* Back on the stock menu, ready to confirm with Yes if that is allowed. */
            panel->cursor = EnterMenu_YesDisabled(panel) ? ENTER_MENU_NO : 0;
        }
        return;
    }
    if (buttons & BTN_A) {
        Sound_Play(SOUND_CONFIRM);
        state->repeatTimer = 0;
        if (state->onName) {
            Edit_OpenName(state, panel);
        } else if (state->col == COL_MOVES && state->row != ROW_LEVEL) {
            Edit_BuildList(state, mon);
            state->mode = EDIT_MOVE_LIST;
        } else {
            state->mode = EDIT_ADJUST;
        }
        return;
    }

    /* The name sits above every column: up from a column's top field reaches it, and
     * down goes back to that field. */
    if (state->onName) {
        if (buttons & BTN_DDOWN) {
            state->onName = FALSE;
            Sound_Play(SOUND_CURSOR);
        }
        return;
    }

    if (buttons & BTN_DUP) {
        if (!Edit_MoveField(state, mon, 0, -1)) {
            state->onName = TRUE;
            Sound_Play(SOUND_CURSOR);
        }
    } else if (buttons & BTN_DDOWN) {
        Edit_MoveField(state, mon, 0, 1);
    } else if (buttons & BTN_DLEFT) {
        Edit_MoveField(state, mon, -1, 0);
    } else if (buttons & BTN_DRIGHT) {
        Edit_MoveField(state, mon, 1, 0);
    }
}

static s32 Edit_Clamp(s32 value, s32 min, s32 max) {
    if (value < min) {
        return min;
    }
    return value > max ? max : value;
}

/* Changes the grabbed number: `steps` small steps, `bigSteps` big ones, or straight to
 * an end of its range when `toEnd` is -1 or 1. */
static void Edit_AdjustField(EditState *state, DetailPanel *panel, s32 steps, s32 bigSteps, s32 toEnd) {
    Pokemon *mon = panel->pokemon;
    s32 old;
    s32 value;
    s32 look;

    if (state->col == COL_DV) {
        old = Edit_GetDv(mon, state->row);
        value = Edit_Clamp(old + steps + bigSteps * DV_BIG_STEP, 0, MAX_DV);
        if (toEnd != 0) {
            value = toEnd < 0 ? 0 : MAX_DV;
        }
        if (value != old) {
            look = Edit_Look(mon);
            Edit_SetDv(mon, state->row, value);
            if (Edit_Look(mon) != look) {
                Edit_ReloadLook(panel);
            }
        }
    } else if (state->col == COL_STAT_EXP) {
        old = mon->statExp[state->row];
        value = Edit_Clamp(StatExpSqrt(old) / 4 + steps + bigSteps * STAT_EXP_BIG_STEP, 0, MAX_STAT_EXP_TIER);
        if (toEnd != 0) {
            value = toEnd < 0 ? 0 : MAX_STAT_EXP_TIER;
        }
        value = Edit_StatExpForTier(value);
        if (value != old) {
            mon->statExp[state->row] = value;
        }
    } else if (state->col == COL_HAPPINESS) {
        old = mon->happiness;
        value = Edit_Clamp(old + steps + bigSteps * HAPPINESS_BIG_STEP, 0, MAX_HAPPINESS);
        if (toEnd != 0) {
            value = toEnd < 0 ? 0 : MAX_HAPPINESS;
        }
        mon->happiness = value;
    } else {
        old = mon->level;
        value = Edit_Clamp(old + steps + bigSteps * LEVEL_BIG_STEP, Edit_MinLevel(), Edit_MaxLevel());
        if (toEnd != 0) {
            value = toEnd < 0 ? Edit_MinLevel() : Edit_MaxLevel();
        }
        if (value != old) {
            value = Edit_SetLevel(panel, value);
        }
    }

    if (value == old) {
        return;
    }
    Edit_Recalculate(panel);
    Sound_Play(SOUND_CURSOR);
}

static void Edit_UpdateAdjust(EditState *state, Pad *pad, DetailPanel *panel) {
    s32 buttons = Edit_RepeatedButtons(&state->repeatTimer, pad, BTN_DUP | BTN_DDOWN);

    if (pad->pressed & (BTN_A | BTN_B)) {
        Sound_Play(SOUND_CONFIRM);
        state->mode = EDIT_FIELDS;
        return;
    }

    if (buttons & BTN_DUP) {
        Edit_AdjustField(state, panel, 1, 0, 0);
    } else if (buttons & BTN_DDOWN) {
        Edit_AdjustField(state, panel, -1, 0, 0);
    } else if (pad->pressed & BTN_DRIGHT) {
        Edit_AdjustField(state, panel, 0, 1, 0);
    } else if (pad->pressed & BTN_DLEFT) {
        Edit_AdjustField(state, panel, 0, -1, 0);
    } else if (pad->pressed & BTN_R) {
        Edit_AdjustField(state, panel, 0, 0, 1);
    } else if (pad->pressed & BTN_L) {
        Edit_AdjustField(state, panel, 0, 0, -1);
    }
}

static void Edit_UpdateList(EditState *state, Pad *pad, DetailPanel *panel) {
    Pokemon *mon = panel->pokemon;
    s32 buttons = Edit_RepeatedButtons(&state->repeatTimer, pad, BTN_DUP | BTN_DDOWN);
    s32 slot = state->row;
    s32 move;

    Edit_GlideScroll(state);
    if (pad->pressed & BTN_B) {
        Sound_Play(SOUND_CANCEL);
        state->mode = EDIT_FIELDS;
        return;
    }
    if (pad->pressed & BTN_A) {
        move = state->list[state->cursor];
        if (move == EDIT_REMOVE) {
            Edit_RemoveMove(mon, slot);
            if (state->row >= Edit_SlotCount(mon)) {
                state->row = Edit_SlotCount(mon) - 1;
            }
        } else if (Edit_Knows(mon, move, slot)) {
            Sound_Play(SOUND_ERROR);
            return;
        } else {
            mon->moves[slot] = move;
            mon->pp[slot] = Move_MaxPP(move, mon->pp[slot]);
        }
        Sound_Play(SOUND_CONFIRM);
        state->mode = EDIT_FIELDS;
        panel->redraw = TRUE;
        return;
    }

    if (buttons & BTN_DUP) {
        Edit_MoveListCursor(state, -1);
    } else if (buttons & BTN_DDOWN) {
        Edit_MoveListCursor(state, 1);
    } else if (pad->pressed & BTN_DLEFT) {
        Edit_MoveListCursor(state, -EDIT_LIST_ROWS);
    } else if (pad->pressed & BTN_DRIGHT) {
        Edit_MoveListCursor(state, EDIT_LIST_ROWS);
    }
}

void Edit_Update(DetailPanel *panel, Pad *pad) {
    EditState *state = Edit_GetState();

    if (state->mode == EDIT_FIELDS) {
        Edit_UpdateFields(state, pad, panel);
    } else if (state->mode == EDIT_ADJUST) {
        Edit_UpdateAdjust(state, pad, panel);
    } else if (state->mode == EDIT_NAME) {
        Edit_UpdateName(state, pad, panel);
    } else {
        Edit_UpdateList(state, pad, panel);
    }
}
