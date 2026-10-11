#include "edit.h"

/* Positions inside the editor window, relative to its top-left corner. Numbers are
 * right-aligned, so their X is where they end. */
#define TITLE_Y 14
#define HEADER_Y 38
#define ROW_Y 60
#define ROW_SPACING 22

#define MOVE_X 26
#define PP_X 216
#define STAT_NAME_X 262
#define DV_X 410
#define STAT_EXP_X 516

#define LIST_ROW_Y 36
#define LIST_ROW_SPACING 19
#define LIST_TYPE_X 236
#define LIST_POWER_X 400
#define LIST_ACCURACY_X 458
#define LIST_PP_X 516

/* The inside of the ENTER menu box, relative to the panel; used for key hints. */
#define SIDEBAR_X (ENTER_MENU_X + 7)
#define SIDEBAR_Y 9
#define SIDEBAR_WIDTH 129
#define SIDEBAR_HEIGHT 128
#define SIDEBAR_TEXT_X (ENTER_MENU_X + 0x12)
#define SIDEBAR_TEXT_Y 0x28
#define SIDEBAR_SPACING 20

static char sTitle[] = "EDIT";
static char sMoves[] = "MOVES";
static char sPP[] = "PP";
static char sDV[] = "DV";
static char sStatExp[] = "STAT EXP";
static char sLevel[] = "LEVEL";
static char sAdd[] = "(add)";
static char sRemove[] = "(remove)";
static char sPickMove[] = "PICK MOVE";
static char sType[] = "TYPE";
static char sPower[] = "POW";
static char sAccuracy[] = "ACC";
static char sDash[] = "-";
static char sSlash[] = "/";

static char sHp[] = "HP";
static char sAttack[] = "ATTACK";
static char sDefense[] = "DEFENSE";
static char sSpeed[] = "SPEED";
static char sSpecial[] = "SPECIAL";
static char *sStatNames[NUM_ROWS] = { sHp, sAttack, sDefense, sSpeed, sSpecial };

static char sHintChange[] = "A: change";
static char sHintDone[] = "B: done";
static char sHintAdjust[] = "Pad: adjust";
static char sHintEnds[] = "L R: min max";
static char sHintOk[] = "A: ok";
static char sHintPick[] = "A: pick";
static char sHintBack[] = "B: back";
static char sHintPage[] = "Sideways: page";

static void Edit_White(void) {
    Text_SetColor(0xFF, 0xFF, 0xFF, 0xFF);
}

static void Edit_Grey(void) {
    Text_SetColor(0x90, 0x90, 0xA0, 0xFF);
}

static void Edit_Heading(void) {
    Text_SetColor(0x80, 0xE0, 0xFF, 0xFF);
}

/* Yellow marks the field the cursor is on, green one whose value is being changed. */
static void Edit_FieldColor(EditState *state, s32 col, s32 row) {
    if (state->col != col || state->row != row) {
        Edit_White();
    } else if (state->mode == EDIT_ADJUST) {
        Text_SetColor(0x60, 0xFF, 0x60, 0xFF);
    } else {
        Text_SetColor(0xFF, 0xFF, 0, 0xFF);
    }
}

static void Edit_DrawRight(s32 x, s32 y, char *str) {
    Text_Draw(x - Text_Width(MENU_FONT, 1, str), y, str);
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

static void Edit_DrawFields(EditState *state, Pokemon *mon) {
    s32 x = EDIT_WINDOW_X;
    s32 y = EDIT_WINDOW_Y;
    s32 moves = Edit_MoveCount(mon);
    s32 row;
    s32 rowY;

    Edit_Heading();
    Text_Draw(x + MOVE_X, y + TITLE_Y, sTitle);
    Text_Draw(x + MOVE_X, y + HEADER_Y, sMoves);
    Edit_DrawRight(x + PP_X, y + HEADER_Y, sPP);
    Edit_DrawRight(x + DV_X, y + HEADER_Y, sDV);
    Edit_DrawRight(x + STAT_EXP_X, y + HEADER_Y, sStatExp);
    Edit_White();
    Text_Draw(x + MOVE_X + 60, y + TITLE_Y, mon->nickname);

    for (row = 0; row < NUM_ROWS; row++) {
        rowY = y + ROW_Y + ROW_SPACING * row;

        Edit_FieldColor(state, COL_MOVES, row);
        if (row == ROW_LEVEL) {
            Text_Draw(x + MOVE_X, rowY, sLevel);
            Edit_DrawNumber(x + PP_X, rowY, mon->level);
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

static void Edit_DrawMoveList(EditState *state, Pokemon *mon) {
    s32 x = EDIT_WINDOW_X;
    s32 y = EDIT_WINDOW_Y;
    char buffer[12];
    s32 row;

    Edit_Heading();
    Text_Draw(x + MOVE_X, y + TITLE_Y, sPickMove);
    Text_Draw(x + LIST_TYPE_X, y + TITLE_Y, sType);
    Edit_DrawRight(x + LIST_POWER_X, y + TITLE_Y, sPower);
    Edit_DrawRight(x + LIST_ACCURACY_X, y + TITLE_Y, sAccuracy);
    Edit_DrawRight(x + LIST_PP_X, y + TITLE_Y, sPP);

    /* Position in the list, e.g. 12/45. */
    Edit_Grey();
    Edit_DrawNumber(x + MOVE_X + 140, y + TITLE_Y, state->cursor + 1);
    Text_Draw(x + MOVE_X + 142, y + TITLE_Y, sSlash);
    Text_Draw(x + MOVE_X + 150, y + TITLE_Y, Edit_Digits(&buffer[11], state->count));

    for (row = 0; row < EDIT_LIST_ROWS && state->top + row < state->count; row++) {
        s32 index = state->top + row;
        s32 move = state->list[index];
        s32 rowY = y + LIST_ROW_Y + LIST_ROW_SPACING * row;

        if (index == state->cursor) {
            Text_SetColor(0xFF, 0xFF, 0, 0xFF);
        } else if (move != EDIT_REMOVE && Edit_Knows(mon, move, state->row)) {
            Edit_Grey();
        } else {
            Edit_White();
        }

        if (move == EDIT_REMOVE) {
            Text_Draw(x + MOVE_X, rowY, sRemove);
            continue;
        }
        Text_Draw(x + MOVE_X, rowY, Move_Name(move));
        Text_Draw(x + LIST_TYPE_X, rowY, Type_Name(Move_Type(move)));
        if (Move_Power(move) > 1) {
            Edit_DrawNumber(x + LIST_POWER_X, rowY, Move_Power(move));
        } else {
            Edit_DrawRight(x + LIST_POWER_X, rowY, sDash);
        }
        Edit_DrawNumber(x + LIST_ACCURACY_X, rowY, (Move_Accuracy(move) * 100 + 127) / 255);
        Edit_DrawNumber(x + LIST_PP_X, rowY, Move_BasePP(move));
    }
}

/* The editor proper: a window over the party box. */
void Edit_DrawWindow(DetailPanel *panel) {
    EditState *state = Edit_GetState();

    Window_Draw(EDIT_WINDOW_X, EDIT_WINDOW_Y, EDIT_WINDOW_WIDTH, EDIT_WINDOW_HEIGHT);

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

/* Key hints, painted over the stock ENTER menu entries. The box's frame stays. */
void Edit_DrawSidebar(DetailPanel *panel) {
    EditState *state = Edit_GetState();
    s32 x = panel->x;
    s32 y = panel->y;
    char *lines[3];
    s32 i;

    lines[2] = NULL;
    if (state->mode == EDIT_FIELDS) {
        lines[0] = sHintChange;
        lines[1] = sHintDone;
    } else if (state->mode == EDIT_ADJUST) {
        lines[0] = sHintAdjust;
        lines[1] = sHintEnds;
        lines[2] = sHintOk;
    } else {
        lines[0] = sHintPick;
        lines[1] = sHintBack;
        lines[2] = sHintPage;
    }

    gSPDisplayList(gDisplayListHead++, D_80094D90);
    Gfx_FillRectRgb(x + SIDEBAR_X, y + SIDEBAR_Y, SIDEBAR_WIDTH, SIDEBAR_HEIGHT, 0x33, 0x33, 0xF8);

    gSPDisplayList(gDisplayListHead++, D_80094F50);
    Text_Begin();
    Text_SetFont(MENU_FONT, 1);
    Edit_Heading();
    Text_Draw(x + ENTER_MENU_X + ENTER_MENU_TITLE_X - Text_Width(MENU_FONT, 1, sTitle) / 2,
              y + ENTER_MENU_TITLE_Y, sTitle);
    Edit_White();
    for (i = 0; i < 3 && lines[i] != NULL; i++) {
        Text_Draw(x + SIDEBAR_TEXT_X, y + SIDEBAR_TEXT_Y + SIDEBAR_SPACING * i, lines[i]);
    }
    Text_End();
}
