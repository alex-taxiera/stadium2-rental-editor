#ifndef MOD_GAME_H
#define MOD_GAME_H

/*
 * Declarations for the parts of the stock game the mod uses. Names on the left are
 * ours; each maps to the address-named symbol in the decompilation. Layouts and
 * signatures are documented in mod/NOTES.md.
 */

#include <ultra64.h>

/* --- Pokemon record (0x58 bytes) --- */

typedef struct Pokemon {
    /* 0x00 */ u8 species;
    /* 0x01 */ u8 item;
    /* 0x02 */ u8 moves[4];
    /* 0x06 */ u16 otId;
    /* 0x08 */ u32 exp;
    /* 0x0C */ u16 statExp[5]; /* HP, Attack, Defense, Speed, Special */
    /* 0x16 */ u16 dvs;
    /* 0x18 */ u8 pp[4];
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

/* --- Detail panel and ENTER menu (fragment 14) --- */

typedef struct DetailPanel {
    /* 0x00 */ u8 unk00[8];
    /* 0x08 */ s16 x;
    /* 0x0A */ s16 y;
    /* 0x0C */ u8 unk0C[0x28];
    /* 0x34 */ u8 state;
    /* 0x35 */ u8 mode;
    /* 0x36 */ s8 cursor;
    /* 0x37 */ u8 unk37[2];
    /* 0x39 */ u8 item;
    /* 0x3A */ u8 unk3A[0x22];
    /* 0x5C */ void *itemList; /* NULL when the rules allow no items */
    /* 0x60 */ u8 unk60[0xC];
    /* 0x6C */ Pokemon *pokemon;
} DetailPanel;

#define PANEL_CLOSED 0
#define PANEL_MODE_ENTER 0
#define PANEL_MODE_EXCHANGE 1

/* Menu geometry, from func_8130DA04. */
#define ENTER_MENU_X 0x191
#define ENTER_MENU_ITEM_X 0x45
#define ENTER_MENU_ITEM_Y 0x26
#define ENTER_MENU_ITEM_SPACING 0x15

/* --- Drawing (main segment) --- */

extern Gfx *D_800D0510;
#define gDisplayListHead D_800D0510

extern Gfx D_80094F50[]; /* render state for text */

void func_800498C4(void);
void func_800496A4(s32 font, s32 arg1);
void func_8004972C(s32 r, s32 g, s32 b, s32 a);
void func_800495BC(s32 x, s32 y, char *str);
void func_800499EC(void);

#define Text_Begin func_800498C4
#define Text_SetFont func_800496A4
#define Text_SetColor func_8004972C
#define Text_Draw func_800495BC
#define Text_End func_800499EC

/* --- Stock functions moved into the mod fragment (see mod/hooks.txt) --- */

void orig_func_8130251C(void);
void orig_func_8130DA04(DetailPanel *panel, s32 arg1);

#endif
