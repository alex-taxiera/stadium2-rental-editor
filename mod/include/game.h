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
#define MAX_HAPPINESS 255

#define SPECIES_UNOWN 201
#define SPECIES_SMEARGLE 235
#define MOVE_RETURN 216
#define MOVE_FRUSTRATION 218
#define MOVE_HIDDEN_POWER 237

/* A name is at most ten characters, the Game Boy's limit, and a zero byte ends it.
 * Registered teams store it in the Game Boy's character codes (func_800615D0), so it
 * may only use characters that have one; see tools/mod/gen_name_keys.py. */
#define MAX_NAME_LENGTH 10

char *func_8004B7A4(s32 species); /* the species name, which is also the default nickname */
#define Species_Name func_8004B7A4

char *HAL_Strcpy(char *dst, char *src);
s32 HAL_Strcmp(char *a, char *b);

void func_800619E8(Pokemon *mon);            /* level from experience, then all six stats */
s32 func_80061B88(s32 species, u16 level);   /* experience needed for a level */
void func_80061F44(Pokemon *mon);            /* full HP, no status, PP refilled */
u16 StatExpSqrt(u16 statExp);                /* the square-root term of the stat formula */

#define Pokemon_RecalcStats func_800619E8
#define Pokemon_ExpForLevel func_80061B88
#define Pokemon_Heal func_80061F44

/* What the DVs decide besides stats. Gender is func_80064474, which the stock detail
 * panel already draws. */
s32 func_8006456C(s32 dvs);  /* 1 for a shiny Pokemon */
s32 func_80064520(u16 dvs);  /* Unown's letter, 1-26 */
s32 func_8003F954(u16 dvs);  /* the colour of Smeargle's paint, 0-8 */

#define Pokemon_IsShiny func_8006456C
#define Unown_Letter func_80064520
#define Smeargle_Paint func_8003F954

/* Type ids run 0-9 (Normal to Steel, with the unused Bird at 6), then 20-27 (Fire to Dark). */
#define TYPE_BIRD 6
#define TYPE_PHYSICAL_END 10
#define TYPE_FIRE 20

/* An entry in the picker's list or party box: the record, where it came from, and the
 * icon drawn for it. Every record the detail panel is given is the start of one. */
typedef struct ListCell {
    /* 0x00 */ Pokemon pokemon;
    /* 0x58 */ u8 source;
    /* 0x59 */ u8 tab;
    /* 0x5A */ u8 index;
    /* 0x5B */ u8 species;
    /* 0x5C */ u8 unk5C[4];
    /* 0x60 */ u8 icon[0xC88];
} ListCell; /* size = 0xCE8 */

s32 func_8004D878(void *icon, s32 arg1, Pokemon *mon); /* renders a record's icon */
#define Icon_Load func_8004D878

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
#define BTN_START 0x1000
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
    /* 0x0C */ u8 unk0C[0x20];
    /* 0x2C */ f32 opening; /* how far open the menu box is, 0 to 1 */
    /* 0x30 */ u8 unk30[4];
    /* 0x34 */ u8 state;
    /* 0x35 */ u8 mode;
    /* 0x36 */ s8 cursor;
    /* 0x37 */ u8 controller;
    /* 0x38 */ s8 unk38;
    /* 0x39 */ u8 item;
    /* 0x3A */ u8 unk3A[0x22];
    /* 0x5C */ void *itemList; /* NULL when the rules allow no items */
    /* 0x60 */ u8 unk60[8];
    /* 0x68 */ void *model; /* the 3D Pokemon beside the panel */
    /* 0x6C */ Pokemon *pokemon;
    /* 0x70 */ s32 modelTimer; /* counts down a frame at a time; at 0 the model is reloaded */
} DetailPanel;

#define PANEL_CLOSED 0
#define PANEL_MENU 1
#define PANEL_CLOSING 3 /* after a choice; the result is the cursor's row plus one */
#define PANEL_MODE_ENTER 0
#define PANEL_MODE_EXCHANGE 1 /* on a Pokemon already on the team: Yes to pick another in its place */
#define ENTER_MENU_NO 1

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

/* --- Popup menus (fragment 14) ---
 *
 * The lists of choices that pop up over the entry screen, such as OK / OK to Register
 * once a team is chosen. A menu is drawn from a definition: where it goes, its font and
 * spacing, and its entries. The screen asks Menu_Poll every frame with the definition it
 * wants shown: that opens the menu, returns 0 while it is up, and then the result of the
 * entry chosen, or `cancelResult`.
 */

typedef struct MenuEntry {
    /* 0x00 */ u16 text; /* in the definition's text bank */
    /* 0x02 */ u16 unk02;
    /* 0x04 */ s16 result;
    /* 0x06 */ s16 centred; /* nonzero to centre the text in the box */
} MenuEntry; /* size = 0x8 */

typedef struct MenuDef {
    /* 0x00 */ u8 unk00[8];
    /* 0x08 */ s16 x; /* the box is placed against this point */
    /* 0x0A */ s16 y;
    /* 0x0C */ s16 alignX;
    /* 0x0E */ s16 alignY;
    /* 0x10 */ s8 marginTop;
    /* 0x11 */ s8 marginBottom;
    /* 0x12 */ s8 marginLeft;
    /* 0x13 */ s8 marginRight;
    /* 0x14 */ s8 font;
    /* 0x15 */ s8 unk15;
    /* 0x16 */ s8 rowSpacing;
    /* 0x17 */ s8 fontArg; /* Text_SetFont's second argument, less two */
    /* 0x18 */ s16 cancelResult;
    /* 0x1A */ u16 unk1A;
    /* 0x1C */ u16 count;
    /* 0x1E */ u16 textBank;
    /* 0x20 */ MenuEntry *entries;
} MenuDef; /* size = 0x24 */

typedef struct Menu {
    /* 0x00 */ MenuDef *def;
    /* 0x04 */ f32 opening; /* 0 closed to 16 open */
    /* 0x08 */ f32 pointerTimer;
    /* 0x0C */ s32 textArg;
    /* 0x10 */ s16 x; /* the box, worked out from the definition when the menu opens */
    /* 0x12 */ s16 y;
    /* 0x14 */ s16 width;
    /* 0x16 */ s16 height;
    /* 0x18 */ u8 status;
    /* 0x19 */ s8 cursor;
    /* 0x1A */ u8 controller;
    /* 0x1B */ u8 unk1B;
    /* 0x1C */ s32 highlight; /* set when the entries' results differ: the cursor's row is yellow */
} Menu;

#define MENU_OPEN 2

s32 func_81311C70(Menu *menu, MenuDef *def, s32 controller, s32 textArg);
#define Menu_Poll func_81311C70

/* --- Trainer pictures ---
 *
 * 64 x 64 pictures, 0x2008 bytes each with their header, in an archive of the ROM: a
 * directory of {offset, size} per trainer, and at each offset a count of expressions and
 * where each one's pixels start. The game reads them through an archive handle that the
 * entry screen does not open, so the mod reads the ROM itself.
 */

#define TRAINER_PICTURES_ROM 0x02268000
#define NUM_TRAINER_PICTURES 67
#define TRAINER_PICTURE_SIZE 64
#define TRAINER_PICTURE_BYTES 0x2008

/* What the game gives every human player: trainer 0x40, looking up. */
#define DEFAULT_TRAINER_PICTURE 0x40
#define DEFAULT_TRAINER_EXPRESSION 1

/* Each player's choice, by controller port: 0 for the game's own picture, else a
 * trainer's number plus one. These are the last four bytes of osAppNMIBuffer, which
 * libultra clears at power on and the game never uses, so a choice lasts until then. The
 * stock code that picks a human's picture is changed to read them (mod/stock_patches.txt). */
#define gTrainerChoices ((u8 *)0x80000358)

/* A player's name and title go with their picture.
 *
 * The name: the picker keeps one per team (`party + PARTY_NAME`), a Game Pak's trainer
 * name or nothing, and when the team is confirmed hands it to the screens that follow,
 * or "1P" to "4P" from the text bank when there is none. The mod's is at most as long as
 * a Game Boy trainer name.
 *
 * The title: every trainer has one on the screens before and after a battle, a number in
 * a bank of them. A player's is always PLAYER_TRAINER_TITLE, POKeMON TRAINER. The bank
 * is not loaded on the entry screen, so the mod reads a title's text from the ROM: a
 * count, that many offsets from the bank's start, then the texts.
 *
 * Both are remembered as gTrainerChoices is, in the bytes of osAppNMIBuffer before it:
 * a name of TRAINER_NAME_BYTES per port, empty for none, and a title per port as its
 * number XOR PLAYER_TRAINER_TITLE, so that nothing chosen is 0. */
#define MAX_TRAINER_NAME 7
#define TRAINER_NAME_BYTES 8
#define gTrainerNames ((char *)0x80000334)
#define gTrainerTitles ((u8 *)0x80000354)
#define TRAINER_TITLES_ROM 0x01D95240
#define PLAYER_TRAINER_TITLE 0x29

#define ENTRY_STATE_PARTY 0x15370 /* in the picker's state: the team being chosen */
#define PARTY_NAME 0x11
#define PARTY_CELLS 0x20 /* its Pokemon, a ListCell each; an empty place has species 0 */
#define PARTY_SIZE 6

/* What the team menu answers for "Reselect some": the cursor goes to the team's box,
 * where A on a Pokemon opens the detail panel on it, to EXCHANGE. */
#define TEAM_MENU_RESELECT_SOME 4

/* The lowest that three of a team's levels come to, which is what the rules' limit on
 * levels together is held against; 600 for a team of fewer than three. A team over the
 * limit is not let back to its menu: the game has its last Pokemon chosen again. */
s32 func_8160A9F0(u8 *party);
#define Party_LowestLevelTotal func_8160A9F0

char *func_8004C874(s32 bank, s32 id); /* a text of a loaded bank */
#define Text_Lookup func_8004C874
#define ENTRY_TEXT_BANK 0xF
#define ENTRY_TEXT_PLAYER 0x62 /* "1P", then 2P to 4P */
#define ENTRY_TEXT_EXCHANGE_WHICH 0x1F /* "Exchange which POKeMON?", over the team's box */

void func_80003F74(void *dst, u32 romStart, u32 romEnd, s32 arg3); /* reads the ROM, and waits for it */
#define Rom_Read func_80003F74

void func_8004D19C(s32 x, s32 y, void *image, s32 arg3, s32 arg4);
#define Image_Draw func_8004D19C

extern Gfx D_80094E38[]; /* render state for images */

/* --- Item list (fragments 11 and 14) ---
 *
 * Items on offer are a mask with one bit per item id. The list built from it holds "No
 * item" and then each item in the mask that the game classes as worth holding.
 */

#define ITEM_MASK_WORDS 8

void func_81601A38(s32 *mask, s32 set); /* every bit of a mask on or off */
#define ItemMask_Fill func_81601A38

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
char *func_816087C8(Pokemon *mon); /* the gender symbol as a string, empty when there is none */

#define Region_Add func_81600A34
#define Region_ShouldDraw func_81600DA8
#define Window_Draw func_816048E0
#define Pokemon_GenderSymbol func_816087C8

/* A window's usable inside, given its outer rectangle. */
#define WINDOW_INSET 8
#define WINDOW_BORDER 19

/* --- Cursors and the scroll bar, as the stock lists and menus draw them --- */

/* Four corner brackets around a rectangle, breathing in and out by two pixels. `phase`
 * is the caller's; one call moves it on an eighth of a cycle when `animate` is set. */
s32 func_8004B09C(s32 x, s32 y, s32 width, s32 height, u16 *phase, u8 r, u8 g, u8 b, s32 animate);
#define Brackets_Draw func_8004B09C
#define BRACKET_CORNER 16 /* a corner is this wide, and a pixel less high */

/* The pointing hand, sliding up to 6 pixels right and back. `timer` is the caller's. */
void func_81608918(s32 x, s32 y, f32 *timer);
#define Pointer_Draw func_81608918
#define POINTER_WIDTH 38 /* the hand, plus how far it slides */

/* A vertical scroll bar with its knob at `position`, 0 for the top to 1 for the bottom.
 * The last two arguments are what the stock lists pass; the function ignores them. */
void func_81607440(s32 x, s32 y, s32 width, s32 height, f32 position, s32 canScrollUp, s32 canScrollDown);
#define ScrollBar_Draw func_81607440
#define SCROLL_BAR_WIDTH 19

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
void orig_func_81306B64(void *list, s32 x, s32 y, s32 arg3, s32 *available);
void orig_func_813114B8(Menu *menu, s32 row);
void orig_func_81302EE4(u8 *party, u8 *state, char *name, s32 id, void *arg4, void *arg5);
void orig_func_81311650(Menu *menu, void *ctx);

#endif
