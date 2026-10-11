#include "edit.h"

#include "name_keys.inc.c"

#define KEY_REPEAT (BTN_DUP | BTN_DDOWN | BTN_DLEFT | BTN_DRIGHT)

s32 Edit_NameKey(s32 page, s32 row, s32 col) {
    return sNameKeys[page][row][col];
}

/* The keyboard starts with the name as it is, so it can be added to or cut back. */
void Edit_OpenName(EditState *state, DetailPanel *panel) {
    char *name = panel->pokemon->nickname;
    s32 length = 0;

    while (length < MAX_NAME_LENGTH && name[length] != '\0') {
        state->name[length] = name[length];
        length++;
    }
    state->name[length] = '\0';
    state->nameLength = length;
    state->keyPage = PAGE_UPPER;
    state->keyRow = 0;
    state->keyCol = 0;
    state->keysMeasured = FALSE;
    state->repeatTimer = 0;
    state->mode = EDIT_NAME;
}

/* The cursor wraps at every edge. On the bottom row it steps between the three wide
 * keys and rests in the middle of one, so going back up lands under it. */
static void Edit_MoveKey(EditState *state, s32 colStep, s32 rowStep) {
    s32 col = state->keyCol;
    s32 row = state->keyRow + rowStep;

    if (row < 0) {
        row = KEY_ROW_WIDE;
    } else if (row > KEY_ROW_WIDE) {
        row = 0;
    }
    if (row == KEY_ROW_WIDE && colStep != 0) {
        col = (col / WIDE_KEY_SPAN + colStep + NUM_WIDE_KEYS) % NUM_WIDE_KEYS;
        col = col * WIDE_KEY_SPAN + WIDE_KEY_SPAN / 2;
    } else {
        col = (col + colStep + KEY_COLS) % KEY_COLS;
    }
    state->keyCol = col;
    state->keyRow = row;
    Sound_Play(SOUND_CURSOR);
}

static void Edit_JumpToEnd(EditState *state) {
    state->keyRow = KEY_ROW_WIDE;
    state->keyCol = KEY_END * WIDE_KEY_SPAN + WIDE_KEY_SPAN / 2;
}

static void Edit_TypeKey(EditState *state, s32 key) {
    if (state->nameLength >= MAX_NAME_LENGTH) {
        Sound_Play(SOUND_ERROR);
        return;
    }
    state->name[state->nameLength++] = key;
    state->name[state->nameLength] = '\0';
    Sound_Play(SOUND_CONFIRM);
    /* A full name leaves nothing to do but finish, as on the Game Boy. */
    if (state->nameLength == MAX_NAME_LENGTH) {
        Edit_JumpToEnd(state);
    }
}

static void Edit_DeleteKey(EditState *state) {
    if (state->nameLength == 0) {
        Sound_Play(SOUND_ERROR);
        return;
    }
    state->name[--state->nameLength] = '\0';
    Sound_Play(SOUND_CANCEL);
}

static void Edit_SwitchPage(EditState *state) {
    state->keyPage = state->keyPage == PAGE_UPPER ? PAGE_LOWER : PAGE_UPPER;
    Sound_Play(SOUND_CURSOR);
}

/* Writes the typed name to the record. No name at all means no nickname, which the
 * game stores as the species name. */
static void Edit_CommitName(EditState *state, DetailPanel *panel) {
    Pokemon *mon = panel->pokemon;
    char *name = state->nameLength != 0 ? state->name : Species_Name(mon->species);

    if (HAL_Strcmp(mon->nickname, name) != 0) {
        HAL_Strcpy(mon->nickname, name);
        panel->redraw = TRUE;
        /* A nickname tints the Pokemon, so its model and icon change with the name. */
        Edit_ReloadLook(panel);
    }
}

void Edit_UpdateName(EditState *state, Pad *pad, DetailPanel *panel) {
    s32 buttons = Edit_RepeatedButtons(state, pad, KEY_REPEAT);
    s32 pressed = pad->pressed;

    if (pressed & BTN_A) {
        if (state->keyRow != KEY_ROW_WIDE) {
            Edit_TypeKey(state, sNameKeys[state->keyPage][state->keyRow][state->keyCol]);
        } else if (state->keyCol / WIDE_KEY_SPAN == KEY_CASE) {
            Edit_SwitchPage(state);
        } else if (state->keyCol / WIDE_KEY_SPAN == KEY_DELETE) {
            Edit_DeleteKey(state);
        } else {
            Edit_CommitName(state, panel);
            Sound_Play(SOUND_CONFIRM);
            state->mode = EDIT_FIELDS;
        }
    } else if (pressed & BTN_B) {
        /* With nothing left to delete, B backs out and the name stays as it was. */
        if (state->nameLength == 0) {
            Sound_Play(SOUND_CANCEL);
            state->mode = EDIT_FIELDS;
        } else {
            Edit_DeleteKey(state);
        }
    } else if (pressed & (BTN_L | BTN_R)) {
        Edit_SwitchPage(state);
    } else if (pressed & BTN_START) {
        Edit_JumpToEnd(state);
        Sound_Play(SOUND_CURSOR);
    } else if (buttons & BTN_DUP) {
        Edit_MoveKey(state, 0, -1);
    } else if (buttons & BTN_DDOWN) {
        Edit_MoveKey(state, 0, 1);
    } else if (buttons & BTN_DLEFT) {
        Edit_MoveKey(state, -1, 0);
    } else if (buttons & BTN_DRIGHT) {
        Edit_MoveKey(state, 1, 0);
    }
}
