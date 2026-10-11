#ifndef MOD_GAME_H
#define MOD_GAME_H

/*
 * Declarations for the parts of the stock game the mod uses. Names on the left are
 * ours; each maps to the address-named symbol in the decompilation. Layouts and
 * signatures are documented in mod/NOTES.md.
 */

#include <ultra64.h>

/* --- Pokemon record (0x58 bytes) --- */

#define MAX_MOVES 4
#define NUM_SPECIES 251
#define NUM_MOVES 251

typedef struct Pokemon {
    /* 0x00 */ u8 species;
    /* 0x01 */ u8 item;
    /* 0x02 */ u8 moves[MAX_MOVES];
    /* 0x06 */ u16 otId;
    /* 0x08 */ u32 exp;
    /* 0x0C */ u16 statExp[5]; /* HP, Attack, Defense, Speed, Special */
    /* 0x16 */ u16 dvs;
    /* 0x18 */ u8 pp[MAX_MOVES]; /* bits 6-7 PP Ups, bits 0-5 PP */
    /* 0x1C */ u8 happiness;
    /* 0x1D */ u8 level;
    /* 0x1E */ u8 flags;
    /* 0x1F */ u8 unk1F;
    /* 0x20 */ u8 pokerus;
    /* 0x21 */ u8 caughtData[2];
    /* 0x23 */ u8 unk23;
    /* 0x24 */ u8 status;
    /* 0x25 */ u8 unk25;
    /* 0x26 */ u16 hp;
    /* 0x28 */ u16 stats[6]; /* max HP, Attack, Defense, Speed, Sp. Atk, Sp. Def */
    /* 0x34 */ char nickname[12];
    /* 0x40 */ char otName[12];
    /* 0x4C */ u8 unk4C[12];
} Pokemon; /* size = 0x58 */

#define POKEMON_FLAG_RENTAL 0x04

#define MIN_LEVEL 2 /* level 1 underflows the Medium Slow experience curve */
#define MAX_DV 15
#define MAX_STAT_EXP 0xFFFF

void func_800619E8(Pokemon *mon);            /* level from experience, then all six stats */
s32 func_80061B88(s32 species, u16 level);   /* experience needed for a level */
void func_80061F44(Pokemon *mon);            /* full HP, no status, PP refilled */
u16 StatExpSqrt(u16 statExp);                /* the square-root term of the stat formula */

#define Pokemon_RecalcStats func_800619E8
#define Pokemon_ExpForLevel func_80061B88
#define Pokemon_Heal func_80061F44

/* Max PP for a move, keeping the PP Up bits of `ppByte`. */
u8 func_80062EB0(u8 move, u8 ppByte);
char *func_80062CE0(u8 move); /* move name */
u8 func_80062D5C(u8 move);    /* power */
u8 func_80062D98(u8 move);    /* type, 0xFF if invalid */
u8 func_80062DD4(u8 move);    /* accuracy, out of 255 */
u8 func_80062E10(u8 move);    /* base PP */
char *func_80063270(u8 type); /* type name */

#define Move_MaxPP func_80062EB0
#define Move_Name func_80062CE0
#define Move_Power func_80062D5C
#define Move_Type func_80062D98
#define Move_Accuracy func_80062DD4
#define Move_BasePP func_80062E10
#define Type_Name func_80063270

/* --- Rules --- */

typedef struct Rules {
    /* 0x00 */ u8 unk00[0x36];
    /* 0x36 */ u8 minLevel;
    /* 0x37 */ u8 maxLevel;
    /* 0x38 */ u16 maxLevelTotal;
} Rules;

/* The entry screen's settings; the rule set in force hangs off it. */
extern u8 *D_8133197C;
#define gEntrySettings D_8133197C
#define ENTRY_SETTINGS_RULES 0x940

/* --- Controllers --- */

typedef struct Pad {
    /* 0x00 */ u8 unk00[8];
    /* 0x08 */ u16 held;
    /* 0x0A */ u16 unk0A;
    /* 0x0C */ u16 pressed;
    /* 0x0E */ u8 unk0E[0x1A];
} Pad; /* size = 0x28 */

extern Pad D_800CE060[4];
#define gPads D_800CE060

#define BTN_A 0x8000
#define BTN_B 0x4000
#define BTN_L 0x0020
#define BTN_R 0x0010
#define BTN_DUP 0x0800
#define BTN_DDOWN 0x0400
#define BTN_DLEFT 0x0200
#define BTN_DRIGHT 0x0100

/* --- Detail panel and ENTER menu (fragment 14) --- */

typedef struct DetailPanel {
    /* 0x00 */ s32 redraw; /* set to repaint the detail panel; cleared by the game */
    /* 0x04 */ s32 confirmSound;
    /* 0x08 */ s16 x;
    /* 0x0A */ s16 y;
    /* 0x0C */ u8 unk0C[0x28];
    /* 0x34 */ u8 state;
    /* 0x35 */ u8 mode;
    /* 0x36 */ s8 cursor;
    /* 0x37 */ u8 controller;
    /* 0x38 */ s8 unk38;
    /* 0x39 */ u8 item;
    /* 0x3A */ u8 unk3A[0x22];
    /* 0x5C */ void *itemList; /* NULL when the rules allow no items */
    /* 0x60 */ u8 unk60[0xC];
    /* 0x6C */ Pokemon *pokemon;
} DetailPanel;

#define PANEL_CLOSED 0
#define PANEL_MENU 1
#define PANEL_MODE_ENTER 0
#define PANEL_MODE_EXCHANGE 1

/* Number of entries in the ENTER menu: 2, or 3 when items are allowed. */
s32 func_8130CEAC(DetailPanel *panel);
#define EnterMenu_StockCount func_8130CEAC

/* Nonzero when "Yes" is greyed out, e.g. for a held item the rules reject. */
s32 func_8130CE3C(DetailPanel *panel);
#define EnterMenu_YesDisabled func_8130CE3C

/* Menu geometry, from func_8130DA04. */
#define ENTER_MENU_X 0x191
#define ENTER_MENU_TITLE_X 0x49
#define ENTER_MENU_TITLE_Y 0xE
#define ENTER_MENU_ITEM_X 0x45
#define ENTER_MENU_ITEM_Y 0x26
#define ENTER_MENU_ITEM_SPACING 0x15

/* --- Screen regions and windows (fragment 11) ---
 *
 * The screen repaints a widget only when its region is dirty. A widget registers its
 * rectangle every frame while it exists; when it stops, whatever it covered is
 * repainted for it.
 */

extern void *D_81331974;
#define gUiContext D_81331974

void func_81600A34(void *ctx, s32 key, s32 dirty, s32 x, s32 y, s32 width, s32 height);
s32 func_81600DA8(void *ctx, s32 key);
void func_816048E0(s32 x, s32 y, s32 width, s32 height); /* framed window, opaque */

#define Region_Add func_81600A34
#define Region_ShouldDraw func_81600DA8
#define Window_Draw func_816048E0

/* A window's usable inside, given its outer rectangle. */
#define WINDOW_INSET 8
#define WINDOW_BORDER 19

/* --- Drawing (main segment) --- */

extern Gfx *D_800D0510;
#define gDisplayListHead D_800D0510

extern Gfx D_80094F50[]; /* render state for text */
extern Gfx D_80094D90[]; /* render state for opaque filled rectangles */

void func_800498C4(void);
void func_800496A4(s32 font, s32 arg1);
void func_8004972C(s32 r, s32 g, s32 b, s32 a);
void func_800495BC(s32 x, s32 y, char *str);
void func_800499EC(void);
s32 func_80049148(s32 font, s32 arg1, char *str);
void Gfx_FillRectRgb(s16 x, s16 y, s16 width, s16 height, u8 r, u8 g, u8 b);

#define Text_Begin func_800498C4
#define Text_SetFont func_800496A4
#define Text_SetColor func_8004972C
#define Text_Draw func_800495BC
#define Text_End func_800499EC
#define Text_Width func_80049148

#define MENU_FONT 4

/* --- Sound --- */

void func_800226C0(s32 id);
#define Sound_Play func_800226C0

#define SOUND_CURSOR 1
#define SOUND_CONFIRM 2
#define SOUND_CANCEL 3
#define SOUND_ERROR 5

/* --- Stock functions moved into the mod fragment (see mod/hooks.txt) --- */

void orig_func_8130251C(void);
void orig_func_8130DA04(DetailPanel *panel, void *ctx);
void orig_func_8130EC9C(DetailPanel *panel);

#endif
