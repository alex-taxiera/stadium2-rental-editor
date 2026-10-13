#include "edit.h"

/* Positions inside the editor window, relative to its top-left corner. Numbers are
 * right-aligned, so their X is where they end. */
#define TITLE_Y 16
#define HEADER_Y 40
#define ROW_Y 62
#define ROW_SPACING 22

#define MOVE_X 26
#define PP_X 216
/* The level's row holds two fields: the level's number ends here, and happiness starts
 * far enough on for either field's brackets to miss the other's text. */
#define LEVEL_X (MOVE_X + 50)
#define HAPPINESS_X (LEVEL_X + 2 * FIELD_MARGIN)
#define STAT_NAME_X 262
#define DV_X 410
#define STAT_EXP_X 516

/* Traits sit on the title row, filling leftwards from the right-hand column. */
#define TRAIT_X STAT_EXP_X
#define TRAIT_GAP 18
#define WORD_GAP 7
#define NAME_X (MOVE_X + 60)

/* The brackets around the field the cursor is on. Their corners stand clear of the text:
 * a corner's width out to either side of it, and high enough that the upper and lower
 * corners do not meet. A number's field is as wide as its longest value. */
#define FIELD_MARGIN BRACKET_CORNER
#define FIELD_RISE 7
#define FIELD_HEIGHT 30
#define DV_WIDTH 22
#define STAT_EXP_WIDTH 48

/* The move list, from the left: the scroll bar down the window's edge beside the rows,
 * the hand, then the names. */
#define LIST_ROW_Y 36
#define LIST_ROW_SPACING 19
#define LIST_BAR_X WINDOW_INSET
#define LIST_BAR_Y 30
#define LIST_BAR_HEIGHT (EDIT_WINDOW_HEIGHT - WINDOW_BORDER + WINDOW_INSET - LIST_BAR_Y)
#define LIST_POINTER_X (LIST_BAR_X + SCROLL_BAR_WIDTH + 3)
#define LIST_NAME_X (LIST_POINTER_X + POINTER_WIDTH + 4)
#define LIST_COUNT_X (LIST_NAME_X + 118) /* where the cursor's place in the list ends */
#define LIST_TYPE_X 236
#define LIST_POWER_X 400
#define LIST_ACCURACY_X 458
#define LIST_PP_X 516

/* The keyboard: the name's ten cells on the title row, over the grid of keys. Both
 * start at KEY_X. A cell not yet typed in has a line under it. */
#define KEY_X 138
#define KEY_Y 46
#define KEY_WIDTH 30
#define KEY_HEIGHT 20
#define KEY_SPACING 22
#define WIDE_KEY_Y 142
#define WIDE_KEY_WIDTH (KEY_WIDTH * WIDE_KEY_SPAN)
#define KEY_BOX_RISE 2 /* how far the cursor's box starts above the text */
#define NAME_CELL_WIDTH 22
#define NAME_LINE_Y 17
#define NAME_LINE_WIDTH 16
#define NAME_LINE_HEIGHT 2
/* A wide key has the picture of the button that does the same from anywhere on the
 * keyboard, before its label, and the cursor's box is high enough for a round one. The
 * shoulder button is bigger: it starts higher, and its shadow wants more room after it. */
#define WIDE_KEY_HEIGHT (BUTTON_SIZE + 2)
#define WIDE_KEY_BOX_RISE (BUTTON_RISE + 1)
#define SHOULDER_RISE 6
#define SHOULDER_GAP 4

/* The inside of the ENTER menu box, relative to the panel; used for key hints. A hint is
 * a button's picture and what it does, placed across the box as "to check TM" is in
 * the stock menu, on the menu's first row. The shoulder buttons are bigger, so their
 * hints are further apart. */
#define SIDEBAR_X (ENTER_MENU_X + 7)
#define SIDEBAR_Y 9
#define SIDEBAR_WIDTH 129
#define SIDEBAR_HEIGHT (128 - (ENTER_MENU_HEIGHT - EDIT_MENU_HEIGHT))
#define SIDEBAR_HINT_X (ENTER_MENU_X + 0xE)
#define SIDEBAR_HINT_Y 0x28
#define SIDEBAR_SHOULDER_SPACING 34

static char sTitle[] = "EDIT";
static char sMoves[] = "MOVES";
static char sPP[] = "PP";
static char sDV[] = "DV";
static char sStatExp[] = "STAT EXP";
static char sLevel[] = "LV";
static char sHappiness[] = "HAPPINESS";
static char sAdd[] = "(add)";
static char sRemove[] = "(remove)";
static char sPickMove[] = "PICK MOVE";
static char sType[] = "TYPE";
static char sPower[] = "POW";
static char sAccuracy[] = "ACC";
static char sDash[] = "-";
static char sSlash[] = "/";
static char sShiny[] = "SHINY";
static char sLetter[] = "LETTER";
static char sName[] = "NAME";
static char sNickname[] = "NICKNAME";
static char sLower[] = "lower";
static char sUpper[] = "UPPER";
static char sDelete[] = "DEL";
static char sEnd[] = "END";

static char sHp[] = "HP";
static char sAttack[] = "ATTACK";
static char sDefense[] = "DEFENSE";
static char sSpeed[] = "SPEED";
static char sSpecial[] = "SPECIAL";
static char *sStatNames[NUM_ROWS] = { sHp, sAttack, sDefense, sSpeed, sSpecial };

static char sHintMin[] = "to min";
static char sHintMax[] = "to max";

static void Edit_White(void) {
    Text_SetColor(0xFF, 0xFF, 0xFF, 0xFF);
}

static void Edit_Grey(void) {
    Text_SetColor(0x90, 0x90, 0xA0, 0xFF);
}

static void Edit_Heading(void) {
    Text_SetColor(0x80, 0xE0, 0xFF, 0xFF);
}

static void Edit_Gold(void) {
    Text_SetColor(0xFF, 0xC8, 0x40, 0xFF);
}

static void Edit_Yellow(void) {
    Text_SetColor(0xFF, 0xFF, 0, 0xFF);
}

/* Yellow marks the field the cursor is on, green one whose value is being changed. */
static void Edit_FieldColor(EditState *state, s32 col, s32 row) {
    if (state->onName || state->col != col || state->row != row) {
        Edit_White();
    } else if (state->mode == EDIT_ADJUST) {
        Text_SetColor(0x60, 0xFF, 0x60, 0xFF);
    } else {
        Edit_Yellow();
    }
}

/* Draws `str` ending at `x`, and returns where it starts. */
static s32 Edit_DrawRight(s32 x, s32 y, char *str) {
    x -= Text_Width(MENU_FONT, 1, str);
    Text_Draw(x, y, str);
    return x;
}

/* Writes `value` in decimal ending at `end`, and returns where it starts. */
static char *Edit_Digits(char *end, s32 value) {
    *end = '\0';
    do {
        *--end = '0' + value % 10;
        value /= 10;
    } while (value != 0);
    return end;
}

static void Edit_DrawNumber(s32 x, s32 y, s32 value) {
    char buffer[12];

    Edit_DrawRight(x, y, Edit_Digits(&buffer[11], value));
}

/* One of the round buttons' pictures. The render state for images must be set. */
void Edit_DrawButton(s32 x, s32 y, s32 button) {
    void *image = Image_Lookup(BUTTON_IMAGES, button);

    if (image != NULL) {
        Image_Draw(x, y, image, 0, 0);
    }
}

/* What the DVs decide besides the stats, each shown only when it applies: Hidden Power's
 * type and power if the Pokemon knows the move, Unown's letter, and shininess. Gender
 * goes beside the name, as in the stock panel. */
static void Edit_DrawTraits(EditState *state, Pokemon *mon, s32 x, s32 y) {
    char buffer[12];
    char letter[2];

    /* On the happiness field they make way for what happiness decides: the power of
     * Return and of Frustration. */
    if (!state->onName && state->col == COL_HAPPINESS) {
        Edit_White();
        x = Edit_DrawRight(x, y, Edit_Digits(&buffer[11], Edit_MovePower(mon, MOVE_FRUSTRATION)));
        Edit_Heading();
        x = Edit_DrawRight(x - WORD_GAP, y, Move_Name(MOVE_FRUSTRATION)) - TRAIT_GAP;
        Edit_White();
        x = Edit_DrawRight(x, y, Edit_Digits(&buffer[11], Edit_MovePower(mon, MOVE_RETURN)));
        Edit_Heading();
        Edit_DrawRight(x - WORD_GAP, y, Move_Name(MOVE_RETURN));
        return;
    }
    if (Edit_Knows(mon, MOVE_HIDDEN_POWER, -1)) {
        Edit_White();
        x = Edit_DrawRight(x, y, Edit_Digits(&buffer[11], Edit_MovePower(mon, MOVE_HIDDEN_POWER)));
        x = Edit_DrawRight(x - WORD_GAP, y, Type_Name(Edit_MoveType(mon, MOVE_HIDDEN_POWER)));
        Edit_Heading();
        x = Edit_DrawRight(x - WORD_GAP, y, Move_Name(MOVE_HIDDEN_POWER)) - TRAIT_GAP;
    }
    if (mon->species == SPECIES_UNOWN) {
        letter[0] = 'A' + Unown_Letter(mon->dvs) - 1;
        letter[1] = '\0';
        Edit_White();
        x = Edit_DrawRight(x, y, letter);
        Edit_Heading();
        x = Edit_DrawRight(x - WORD_GAP, y, sLetter) - TRAIT_GAP;
    }
    if (Pokemon_IsShiny(mon->dvs)) {
        Edit_Gold();
        Edit_DrawRight(x, y, sShiny);
    }
}

static void Edit_DrawFields(EditState *state, Pokemon *mon) {
    s32 x = EDIT_WINDOW_X;
    s32 y = EDIT_WINDOW_Y;
    s32 moves = Edit_MoveCount(mon);
    s32 row;
    s32 rowY;

    Edit_Heading();
    Text_Draw(x + MOVE_X, y + TITLE_Y, sName);
    Text_Draw(x + MOVE_X, y + HEADER_Y, sMoves);
    Edit_DrawRight(x + PP_X, y + HEADER_Y, sPP);
    Edit_DrawRight(x + DV_X, y + HEADER_Y, sDV);
    Edit_DrawRight(x + STAT_EXP_X, y + HEADER_Y, sStatExp);
    if (state->onName) {
        Edit_Yellow();
    } else {
        Edit_White();
    }
    Text_Draw(x + NAME_X, y + TITLE_Y, mon->nickname);
    Edit_White();
    Text_Draw(x + NAME_X + Text_Width(MENU_FONT, 1, mon->nickname), y + TITLE_Y, Pokemon_GenderSymbol(mon));
    Edit_DrawTraits(state, mon, x + TRAIT_X, y + TITLE_Y);

    for (row = 0; row < NUM_ROWS; row++) {
        rowY = y + ROW_Y + ROW_SPACING * row;

        Edit_FieldColor(state, COL_MOVES, row);
        if (row == ROW_LEVEL) {
            Text_Draw(x + MOVE_X, rowY, sLevel);
            Edit_DrawNumber(x + LEVEL_X, rowY, mon->level);
            Edit_FieldColor(state, COL_HAPPINESS, row);
            Text_Draw(x + HAPPINESS_X, rowY, sHappiness);
            Edit_DrawNumber(x + PP_X, rowY, mon->happiness);
        } else if (row < moves) {
            Text_Draw(x + MOVE_X, rowY, Move_Name(mon->moves[row]));
            Edit_DrawNumber(x + PP_X, rowY, mon->pp[row] & 0x3F);
        } else if (row == moves) {
            Text_Draw(x + MOVE_X, rowY, sAdd);
        }

        Edit_White();
        Text_Draw(x + STAT_NAME_X, rowY, sStatNames[row]);

        if (row == ROW_HP) {
            Edit_Grey();
        } else {
            Edit_FieldColor(state, COL_DV, row);
        }
        Edit_DrawNumber(x + DV_X, rowY, Edit_GetDv(mon, row));

        Edit_FieldColor(state, COL_STAT_EXP, row);
        Edit_DrawNumber(x + STAT_EXP_X, rowY, mon->statExp[row]);
    }
}

/* The cursor of the field menu: the brackets the stock lists use, around the field the
 * cursor is on, gold as theirs are and green while its value is being changed. They go
 * down before the text. */
static void Edit_DrawFieldCursor(EditState *state, Pokemon *mon) {
    s32 x = EDIT_WINDOW_X;
    s32 y = EDIT_WINDOW_Y;
    s32 width;

    if (state->onName) {
        x += NAME_X;
        y += TITLE_Y;
        width = Text_Width(MENU_FONT, 1, mon->nickname) + Text_Width(MENU_FONT, 1, Pokemon_GenderSymbol(mon));
    } else {
        y += ROW_Y + ROW_SPACING * state->row;
        if (state->col == COL_MOVES) {
            x += MOVE_X;
            width = (state->row == ROW_LEVEL ? LEVEL_X : PP_X) - MOVE_X;
        } else if (state->col == COL_HAPPINESS) {
            x += HAPPINESS_X;
            width = PP_X - HAPPINESS_X;
        } else if (state->col == COL_DV) {
            x += DV_X - DV_WIDTH;
            width = DV_WIDTH;
        } else {
            x += STAT_EXP_X - STAT_EXP_WIDTH;
            width = STAT_EXP_WIDTH;
        }
    }
    x -= FIELD_MARGIN;
    width += 2 * FIELD_MARGIN;

    if (state->mode == EDIT_ADJUST) {
        Brackets_Draw(x, y - FIELD_RISE, width, FIELD_HEIGHT, &state->bracketPhase, 0x60, 0xFF, 0x60, TRUE);
    } else {
        Brackets_Draw(x, y - FIELD_RISE, width, FIELD_HEIGHT, &state->bracketPhase, 0xF0, 0xD4, 0x68, TRUE);
    }
}

/* What the move list borrows from the stock lists and menus: a scroll bar, and the hand
 * pointing at the row the cursor is on. They go down before the text. */
static void Edit_DrawListCursor(EditState *state) {
    s32 x = EDIT_WINDOW_X;
    s32 y = EDIT_WINDOW_Y;

    ScrollBar_Draw(x + LIST_BAR_X, y + LIST_BAR_Y, SCROLL_BAR_WIDTH, LIST_BAR_HEIGHT,
                   (f32)state->scroll / SCROLL_UNITS, state->top > 0,
                   state->top + EDIT_LIST_ROWS < state->count);
    Pointer_Draw(x + LIST_POINTER_X, y + LIST_ROW_Y + LIST_ROW_SPACING * (state->cursor - state->top),
                 &state->pointerTimer);
}

static void Edit_DrawMoveList(EditState *state, Pokemon *mon) {
    s32 x = EDIT_WINDOW_X;
    s32 y = EDIT_WINDOW_Y;
    char buffer[12];
    s32 row;

    Edit_Heading();
    Text_Draw(x + LIST_NAME_X, y + TITLE_Y, sPickMove);
    Text_Draw(x + LIST_TYPE_X, y + TITLE_Y, sType);
    Edit_DrawRight(x + LIST_POWER_X, y + TITLE_Y, sPower);
    Edit_DrawRight(x + LIST_ACCURACY_X, y + TITLE_Y, sAccuracy);
    Edit_DrawRight(x + LIST_PP_X, y + TITLE_Y, sPP);

    /* Position in the list, e.g. 12/45. */
    Edit_Grey();
    Edit_DrawNumber(x + LIST_COUNT_X, y + TITLE_Y, state->cursor + 1);
    Text_Draw(x + LIST_COUNT_X + 2, y + TITLE_Y, sSlash);
    Text_Draw(x + LIST_COUNT_X + 10, y + TITLE_Y, Edit_Digits(&buffer[11], state->count));

    for (row = 0; row < EDIT_LIST_ROWS && state->top + row < state->count; row++) {
        s32 index = state->top + row;
        s32 move = state->list[index];
        s32 rowY = y + LIST_ROW_Y + LIST_ROW_SPACING * row;

        if (index == state->cursor) {
            Edit_Yellow();
        } else if (move != EDIT_REMOVE && Edit_Knows(mon, move, state->row)) {
            Edit_Grey();
        } else {
            Edit_White();
        }

        if (move == EDIT_REMOVE) {
            Text_Draw(x + LIST_NAME_X, rowY, sRemove);
            continue;
        }
        Text_Draw(x + LIST_NAME_X, rowY, Move_Name(move));
        Text_Draw(x + LIST_TYPE_X, rowY, Type_Name(Edit_MoveType(mon, move)));
        if (Edit_MovePower(mon, move) > 1 || move == MOVE_RETURN || move == MOVE_FRUSTRATION) {
            Edit_DrawNumber(x + LIST_POWER_X, rowY, Edit_MovePower(mon, move));
        } else {
            Edit_DrawRight(x + LIST_POWER_X, rowY, sDash);
        }
        Edit_DrawNumber(x + LIST_ACCURACY_X, rowY, (Move_Accuracy(move) * 100 + 127) / 255);
        Edit_DrawNumber(x + LIST_PP_X, rowY, Move_BasePP(move));
    }
}

/* The keyboard's filled parts, which go down before its text: a box behind the key the
 * cursor is on, and a line under each cell of the name still to be typed, the next one
 * in yellow. */
static void Edit_DrawNameBoxes(EditState *state) {
    s32 x = EDIT_WINDOW_X + KEY_X;
    s32 y = EDIT_WINDOW_Y;
    s32 i;

    if (state->keyRow == KEY_ROW_WIDE) {
        Gfx_FillRectRgb(x + WIDE_KEY_WIDTH * (state->keyCol / WIDE_KEY_SPAN), y + WIDE_KEY_Y - WIDE_KEY_BOX_RISE,
                        WIDE_KEY_WIDTH, WIDE_KEY_HEIGHT, 0x10, 0x10, 0x80);
    } else {
        Gfx_FillRectRgb(x + KEY_WIDTH * state->keyCol, y + KEY_Y + KEY_SPACING * state->keyRow - KEY_BOX_RISE,
                        KEY_WIDTH, KEY_HEIGHT, 0x10, 0x10, 0x80);
    }
    for (i = state->nameLength; i < state->nameMax; i++) {
        if (i == state->nameLength) {
            Gfx_FillRectRgb(x + NAME_CELL_WIDTH * i, y + TITLE_Y + NAME_LINE_Y, NAME_LINE_WIDTH,
                            NAME_LINE_HEIGHT, 0xFF, 0xFF, 0);
        } else {
            Gfx_FillRectRgb(x + NAME_CELL_WIDTH * i, y + TITLE_Y + NAME_LINE_Y, NAME_LINE_WIDTH,
                            NAME_LINE_HEIGHT, 0x90, 0x90, 0xA0);
        }
    }
}

/* Measuring text is slow, and the keys never change, so each key's place in its cell
 * is worked out once when the keyboard opens. */
static void Edit_MeasureKeys(EditState *state) {
    char key[2];
    s32 page;
    s32 row;
    s32 col;

    key[1] = '\0';
    for (page = 0; page < NUM_PAGES; page++) {
        for (row = 0; row < KEY_ROWS; row++) {
            for (col = 0; col < KEY_COLS; col++) {
                key[0] = Edit_NameKey(page, row, col);
                state->keyInset[page][row][col] = (KEY_WIDTH - Text_Width(MENU_FONT, 1, key)) / 2;
            }
        }
    }
    state->keysMeasured = TRUE;
}

/* The first wide key names the page it switches to, as on the Game Boy. */
static char *Edit_WideKeyLabel(EditState *state, s32 key) {
    if (key == KEY_CASE) {
        return state->keyPage == PAGE_UPPER ? sLower : sUpper;
    }
    return key == KEY_DELETE ? sDelete : sEnd;
}

/* From where a wide key's picture starts to where its label does. */
static s32 Edit_WideKeyPicture(s32 key) {
    return key == KEY_CASE ? SHOULDER_WIDTH + SHOULDER_GAP : BUTTON_SIZE + BUTTON_GAP;
}

/* Where a wide key's picture starts, for it and the label to be in the middle of the
 * key together. */
static s32 Edit_WideKeyX(EditState *state, s32 key) {
    return EDIT_WINDOW_X + KEY_X + WIDE_KEY_WIDTH * key +
           (WIDE_KEY_WIDTH - Edit_WideKeyPicture(key) - Text_Width(MENU_FONT, 1, Edit_WideKeyLabel(state, key))) / 2;
}

/* The wide keys' pictures, which go down before the text: either shoulder button
 * switches the page, B deletes and START goes to END. */
static void Edit_DrawKeyButtons(EditState *state) {
    s32 y = EDIT_WINDOW_Y + WIDE_KEY_Y;

    ShoulderR_Draw(Edit_WideKeyX(state, KEY_CASE), y - SHOULDER_RISE);
    gSPDisplayList(gDisplayListHead++, D_80094E38);
    Edit_DrawButton(Edit_WideKeyX(state, KEY_DELETE), y - BUTTON_RISE, BUTTON_B);
    Edit_DrawButton(Edit_WideKeyX(state, KEY_END), y - BUTTON_RISE, BUTTON_START);
}

static void Edit_DrawName(EditState *state, char *heading) {
    s32 x = EDIT_WINDOW_X + KEY_X;
    s32 y = EDIT_WINDOW_Y;
    char key[2];
    s32 row;
    s32 col;
    s32 i;

    if (!state->keysMeasured) {
        Edit_MeasureKeys(state);
    }
    key[1] = '\0';

    Edit_Heading();
    Text_Draw(EDIT_WINDOW_X + MOVE_X, y + TITLE_Y, heading);

    Edit_White();
    for (i = 0; i < state->nameLength; i++) {
        key[0] = state->name[i];
        Text_Draw(x + NAME_CELL_WIDTH * i + (NAME_LINE_WIDTH - Text_Width(MENU_FONT, 1, key)) / 2, y + TITLE_Y, key);
    }

    for (row = 0; row < KEY_ROWS; row++) {
        for (col = 0; col < KEY_COLS; col++) {
            key[0] = Edit_NameKey(state->keyPage, row, col);
            if (row == state->keyRow && col == state->keyCol) {
                Edit_Yellow();
            }
            Text_Draw(x + KEY_WIDTH * col + state->keyInset[state->keyPage][row][col],
                      y + KEY_Y + KEY_SPACING * row, key);
            if (row == state->keyRow && col == state->keyCol) {
                Edit_White();
            }
        }
    }

    for (i = 0; i < NUM_WIDE_KEYS; i++) {
        if (state->keyRow == KEY_ROW_WIDE && state->keyCol / WIDE_KEY_SPAN == i) {
            Edit_Yellow();
        } else {
            Edit_White();
        }
        Text_Draw(Edit_WideKeyX(state, i) + Edit_WideKeyPicture(i), y + WIDE_KEY_Y, Edit_WideKeyLabel(state, i));
    }
}

/* The keyboard in the editor's window, under whatever the name being typed is called. */
void Edit_DrawKeyboard(EditState *state, char *heading) {
    Window_Draw(EDIT_WINDOW_X, EDIT_WINDOW_Y, EDIT_WINDOW_WIDTH, EDIT_WINDOW_HEIGHT);
    gSPDisplayList(gDisplayListHead++, D_80094D90);
    Edit_DrawNameBoxes(state);
    Edit_DrawKeyButtons(state);

    gSPDisplayList(gDisplayListHead++, D_80094F50);
    Text_Begin();
    Text_SetFont(MENU_FONT, 1);
    Edit_DrawName(state, heading);
    Text_End();
}

/* The editor proper: a window over the party box. */
void Edit_DrawWindow(DetailPanel *panel) {
    EditState *state = Edit_GetState();

    if (state->mode == EDIT_NAME) {
        Edit_DrawKeyboard(state, sNickname);
        return;
    }
    Window_Draw(EDIT_WINDOW_X, EDIT_WINDOW_Y, EDIT_WINDOW_WIDTH, EDIT_WINDOW_HEIGHT);
    if (state->mode == EDIT_MOVE_LIST) {
        Edit_DrawListCursor(state);
    } else {
        Edit_DrawFieldCursor(state, panel->pokemon);
    }

    gSPDisplayList(gDisplayListHead++, D_80094F50);
    Text_Begin();
    Text_SetFont(MENU_FONT, 1);
    if (state->mode == EDIT_MOVE_LIST) {
        Edit_DrawMoveList(state, panel->pokemon);
    } else {
        Edit_DrawFields(state, panel->pokemon);
    }
    Text_End();
}

/* Key hints, painted over the stock ENTER menu entries. The box's frame stays. They are
 * the stock menus' kind, a button's picture and what it does, and only for what the
 * cursor does not say: "to quit" as the ITEM list has it, and the shoulder buttons while
 * a number is grabbed. The keyboard has its own on its keys. */
void Edit_DrawSidebar(DetailPanel *panel) {
    EditState *state = Edit_GetState();
    s32 x = panel->x;
    s32 y = panel->y;
    s32 hintX = x + SIDEBAR_HINT_X;
    s32 hintY = y + SIDEBAR_HINT_Y;

    gSPDisplayList(gDisplayListHead++, D_80094D90);
    Gfx_FillRectRgb(x + SIDEBAR_X, y + SIDEBAR_Y, SIDEBAR_WIDTH, SIDEBAR_HEIGHT, 0x33, 0x33, 0xF8);

    if (state->mode == EDIT_ADJUST) {
        ShoulderL_Draw(hintX, hintY - SHOULDER_RISE);
        ShoulderR_Draw(hintX, hintY - SHOULDER_RISE + SIDEBAR_SHOULDER_SPACING);
    } else if (state->mode != EDIT_NAME) {
        gSPDisplayList(gDisplayListHead++, D_80094E38);
        Edit_DrawButton(hintX, hintY - BUTTON_RISE, BUTTON_B);
    }

    gSPDisplayList(gDisplayListHead++, D_80094F50);
    Text_Begin();
    Text_SetFont(MENU_FONT, 1);
    Edit_Heading();
    Text_Draw(x + ENTER_MENU_X + ENTER_MENU_TITLE_X - Text_Width(MENU_FONT, 1, sTitle) / 2,
              y + ENTER_MENU_TITLE_Y, sTitle);
    Edit_White();
    if (state->mode == EDIT_ADJUST) {
        hintX += SHOULDER_WIDTH + SHOULDER_GAP;
        Text_Draw(hintX, hintY, sHintMin);
        Text_Draw(hintX, hintY + SIDEBAR_SHOULDER_SPACING, sHintMax);
    } else if (state->mode != EDIT_NAME) {
        Text_Draw(hintX + BUTTON_SIZE + BUTTON_GAP, hintY, Text_Lookup(ENTRY_TEXT_BANK, ENTRY_TEXT_TO_QUIT));
    }
    Text_End();
}
