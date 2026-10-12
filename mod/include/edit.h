#ifndef MOD_EDIT_H
#define MOD_EDIT_H

#include "game.h"

enum {
    EDIT_OFF,
    EDIT_FIELDS,   /* moving between fields */
    EDIT_ADJUST,   /* a number is grabbed and the pad changes it */
    EDIT_MOVE_LIST, /* choosing a move from the legal list */
    EDIT_NAME      /* typing a nickname on the keyboard */
};

/* Fields are addressed as (column, row). Rows line up across the three columns. */
enum { COL_MOVES, COL_DV, COL_STAT_EXP, NUM_COLS };

#define NUM_ROWS 5
#define ROW_LEVEL 4 /* in COL_MOVES, below the four moves */
#define ROW_HP 0    /* in COL_DV the HP row is derived, so it cannot be selected */

#define EDIT_LIST_ROWS 7
#define EDIT_REMOVE 0 /* list entry that clears the slot */

/* The nickname keyboard, laid out like the Game Boy's: pages of four rows of nine
 * character keys, above a row of three wide keys that each span three columns. */
enum { PAGE_UPPER, PAGE_LOWER, NUM_PAGES };
#define KEY_ROWS 4
#define KEY_COLS 9
#define KEY_ROW_WIDE KEY_ROWS
enum { KEY_CASE, KEY_DELETE, KEY_END, NUM_WIDE_KEYS };
#define WIDE_KEY_SPAN (KEY_COLS / NUM_WIDE_KEYS)

typedef struct EditState {
    /* 0x00 */ u8 mode;
    /* 0x01 */ u8 col;
    /* 0x02 */ u8 row;
    /* 0x03 */ u8 repeatTimer;
    /* 0x04 */ s16 count;  /* entries in list */
    /* 0x06 */ s16 cursor; /* selected entry */
    /* 0x08 */ s16 top;    /* first visible entry */
    /* 0x0A */ u8 onName;  /* the cursor is on the name; col and row say where it came from */
    /* 0x0B */ u8 keyPage;
    /* 0x0C */ DetailPanel *panel;
    /* 0x10 */ u8 list[NUM_MOVES + 1];
    /* 0x10C */ u8 keyCol;
    /* 0x10D */ u8 keyRow;
    /* 0x10E */ u8 nameLength;
    /* 0x10F */ u8 keysMeasured;
    /* 0x110 */ char name[MAX_NAME_LENGTH + 1]; /* as typed; written to the record on END */
    /* 0x11B */ u8 keyInset[NUM_PAGES][KEY_ROWS][KEY_COLS]; /* centres each key in its cell */
    /* 0x164 */ u16 bracketPhase; /* where the brackets around a field are in their cycle */
    /* 0x166 */ s16 scroll;       /* the scroll bar's knob, 0 to SCROLL_UNITS, gliding to where the list is */
    /* 0x168 */ f32 pointerTimer; /* where the hand in the move list is in its slide */
} EditState; /* size = 0x16C */

#define SCROLL_UNITS 256

/* The editor window, drawn over the party box. The stock detail panel below it stays
 * visible and shows the Pokemon as it will be. */
#define EDIT_WINDOW_X 47
#define EDIT_WINDOW_Y 68
#define EDIT_WINDOW_WIDTH 546
#define EDIT_WINDOW_HEIGHT 186

/* Defined in state.s so C code never takes the address of a field directly: the
 * fragment loader cannot relocate two addresses that share one `lui`. */
EditState *Edit_GetState(void);

/* edit.c */
s32 Edit_CanEdit(DetailPanel *panel);
s32 Edit_IsActive(DetailPanel *panel);
void Edit_Open(DetailPanel *panel);
void Edit_Update(DetailPanel *panel, Pad *pad);
s32 Edit_MoveCount(Pokemon *mon);
s32 Edit_SlotCount(Pokemon *mon);
s32 Edit_Knows(Pokemon *mon, s32 move, s32 exceptSlot);
s32 Edit_HpDv(Pokemon *mon);
s32 Edit_GetDv(Pokemon *mon, s32 row);
s32 Edit_MoveType(Pokemon *mon, s32 move);
s32 Edit_MovePower(Pokemon *mon, s32 move);
s32 Edit_RepeatedButtons(EditState *state, Pad *pad, s32 repeating);
void Edit_ReloadLook(DetailPanel *panel);

/* edit_name.c */
void Edit_OpenName(EditState *state, DetailPanel *panel);
void Edit_UpdateName(EditState *state, Pad *pad, DetailPanel *panel);
s32 Edit_NameKey(s32 page, s32 row, s32 col);

/* edit_draw.c */
void Edit_DrawWindow(DetailPanel *panel);
void Edit_DrawSidebar(DetailPanel *panel);

#endif
