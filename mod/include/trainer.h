#ifndef MOD_TRAINER_H
#define MOD_TRAINER_H

#include "game.h"

/* The team menu with "Edit POKeMON" and "Change Trainer" added is a copy of the stock
 * one, kept here. */
#define TEAM_MENU_MAX_ENTRIES 8
/* The new entries' results: ones the stock code that reads the menu does nothing with. */
#define MENU_RESULT_TRAINER 0x7F
#define MENU_RESULT_EDIT 0x7E

/* Which of the two a menu has been given. */
#define TEAM_MENU_EDIT 1
#define TEAM_MENU_TRAINER 2

/* The trainer window's rows. */
enum { TRAINER_PICTURE, TRAINER_NAME, TRAINER_TITLE, NUM_TRAINER_ROWS };

#define TRAINER_TITLE_BYTES 0x20 /* read from the ROM for a title's text; the longest is 15 */

typedef struct TrainerState {
    /* 0x00 */ u8 open;       /* the trainer window is up, in place of the team menu */
    /* 0x01 */ u8 controller; /* whose pad drives it */
    /* 0x02 */ u8 port;       /* whose picture, name and title it changes */
    /* 0x03 */ u8 choice;     /* the picture, as in gTrainerChoices: 0, or a trainer's number plus one */
    /* 0x04 */ u8 repeatTimer;
    /* 0x05 */ u8 row;
    /* 0x06 */ u16 bracketPhase;
    /* 0x08 */ Menu *owner;     /* the menu the window stands in for */
    /* 0x0C */ MenuDef *source; /* the stock definition `menu` was copied from */
    /* 0x10 */ s32 minWidth;    /* of the menu's box, for the new entries to fit */
    /* 0x14 */ MenuDef menu;
    /* 0x38 */ MenuEntry entries[TEAM_MENU_MAX_ENTRIES];
    /* 0x78 */ u32 header[4]; /* a few words of a table, as read from the ROM */
    /* 0x88 */ u8 picture[TRAINER_PICTURE_BYTES];
    /* 0x2090 */ u8 typing;      /* the keyboard is up, in place of the window */
    /* 0x2091 */ u8 title;       /* which of sTrainerTitles */
    /* 0x2092 */ u8 nameChanged; /* a name was typed, so A keeps it */
    /* 0x2093 */ u8 titleStart;  /* where in `titleText` the title begins: a read starts on an even address */
    /* 0x2094 */ char name[TRAINER_NAME_BYTES]; /* empty for the name the game would give */
    /* 0x209C */ u8 extras;      /* which entries `menu` was given: TEAM_MENU_EDIT, TEAM_MENU_TRAINER */
    /* 0x209D */ u8 unk209D[3];
    /* 0x20A0 */ char titleText[TRAINER_TITLE_BYTES];
} TrainerState; /* size = 0x20C0 */

/* Defined in state.s, like Edit_GetState. */
TrainerState *Trainer_GetState(void);

#endif
