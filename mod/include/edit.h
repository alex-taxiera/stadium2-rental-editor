#ifndef MOD_EDIT_H
#define MOD_EDIT_H

#include "game.h"

enum {
    EDIT_OFF,
    EDIT_FIELDS,   /* moving between fields */
    EDIT_ADJUST,   /* a number is grabbed and the pad changes it */
    EDIT_MOVE_LIST /* choosing a move from the legal list */
};

/* Fields are addressed as (column, row). Rows line up across the three columns. */
enum { COL_MOVES, COL_DV, COL_STAT_EXP, NUM_COLS };

#define NUM_ROWS 5
#define ROW_LEVEL 4 /* in COL_MOVES, below the four moves */
#define ROW_HP 0    /* in COL_DV the HP row is derived, so it cannot be selected */

#define EDIT_LIST_ROWS 7
#define EDIT_REMOVE 0 /* list entry that clears the slot */

typedef struct EditState {
    /* 0x00 */ u8 mode;
    /* 0x01 */ u8 col;
    /* 0x02 */ u8 row;
    /* 0x03 */ u8 repeatTimer;
    /* 0x04 */ s16 count;  /* entries in list */
    /* 0x06 */ s16 cursor; /* selected entry */
    /* 0x08 */ s16 top;    /* first visible entry */
    /* 0x0C */ DetailPanel *panel;
    /* 0x10 */ u8 list[NUM_MOVES + 1];
} EditState;

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

/* edit_draw.c */
void Edit_DrawWindow(DetailPanel *panel);
void Edit_DrawSidebar(DetailPanel *panel);

#endif
