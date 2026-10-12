#include "edit.h"
#include "trainer.h"

#include "trainer_titles.inc.c"

#define NUM_TITLES ((s32)sizeof(sTrainerTitles))

/* The trainer window, over where the team menu was: the picture on the left with its
 * place in the ring under it, the name and title on the right, key hints below. */
#define WINDOW_WIDTH 420
#define WINDOW_HEIGHT 196
#define WINDOW_X ((640 - WINDOW_WIDTH) / 2)
#define WINDOW_Y 255
#define TITLE_Y 14
#define PICTURE_X 34
#define PICTURE_Y 46
#define PICTURE_MARGIN 12 /* from the picture out to the brackets around it */
#define COUNT_Y 126
#define LABEL_X 140
#define VALUE_X 214
#define NAME_Y 60
#define TITLE_ROW_Y 92
#define HINT_Y 146
#define HINT_SPACING 18

/* The brackets around the name or the title, as around a field of the editor. */
#define FIELD_MARGIN BRACKET_CORNER
#define FIELD_RISE 7
#define FIELD_HEIGHT 30

/* The picker's state is found from the menu inside it. */
#define ENTRY_STATE_MENU 0x74
#define ENTRY_STATE_SIDE 0x1A142 /* s8: whose team is being chosen */
#define ENTRY_SETTINGS_PORTS 0x900 /* s8 per side: its controller port, negative for the COM */

/* The window's region is identified by the address of this feature's state, and the
 * keyboard's, which is elsewhere on the screen, by the address after it. */
#define TRAINER_REGION_KEY ((s32)Trainer_GetState())
#define KEYBOARD_REGION_KEY (TRAINER_REGION_KEY + 1)

static char sChangeTrainer[] = "Change Trainer";
static char sHeading[] = "TRAINER";
static char sName[] = "NAME";
static char sTitle[] = "TITLE";
static char sSlash[] = "/";
static char sHintChange[] = "Left Right: change   A: ok";
static char sHintType[] = "A: type";
static char sHintMove[] = "Up Down: move   B: back";

/* The controller port of the side whose team is being chosen, negative for the COM. */
static s32 Trainer_SidePort(u8 *state) {
    return *(s8 *)(gEntrySettings + ENTRY_SETTINGS_PORTS + *(s8 *)(state + ENTRY_STATE_SIDE));
}

static u8 *Trainer_EntryState(Menu *menu) {
    return (u8 *)menu - ENTRY_STATE_MENU;
}

/* Reads the picture for the current choice from the ROM: the directory entry of its
 * trainer, the trainer's table of expressions, then the pixels. */
static void Trainer_LoadPicture(TrainerState *state) {
    s32 trainer = DEFAULT_TRAINER_PICTURE;
    s32 expression = DEFAULT_TRAINER_EXPRESSION;
    u32 rom;

    if (state->choice != 0) {
        trainer = state->choice - 1;
        expression = 0;
    }
    rom = TRAINER_PICTURES_ROM + 0x10 + trainer * 0x10;
    Rom_Read(state->header, rom, rom + 0x10, 0);
    rom = TRAINER_PICTURES_ROM + state->header[0];
    Rom_Read(state->header, rom, rom + 0x10, 0);
    rom += state->header[1 + expression] - 8;
    Rom_Read(state->picture, rom, rom + TRAINER_PICTURE_BYTES, 0);
}

/* Reads the current title's text from the ROM: its offset in the bank, then the text. */
static void Trainer_LoadTitle(TrainerState *state) {
    u32 rom = TRAINER_TITLES_ROM + 4 + sTrainerTitles[state->title] * 4;

    Rom_Read(state->header, rom, rom + 8, 0);
    rom = TRAINER_TITLES_ROM + state->header[0];
    state->titleStart = rom & 1;
    rom -= state->titleStart;
    Rom_Read(state->titleText, rom, rom + TRAINER_TITLE_BYTES, 0);
    state->titleText[TRAINER_TITLE_BYTES - 1] = '\0';
}

/* The stock team menu with "Change Trainer" as one more entry, or the stock one itself
 * where the entry has no place: the COM's team has no player behind it. */
static MenuDef *Trainer_ExtendMenu(TrainerState *state, Menu *menu, MenuDef *def) {
    s32 i;

    if (def == NULL || def->count >= TEAM_MENU_MAX_ENTRIES || Trainer_SidePort(Trainer_EntryState(menu)) < 0) {
        return def;
    }
    if (state->source != def) {
        state->source = def;
        state->menu = *def;
        for (i = 0; i < def->count; i++) {
            state->entries[i] = def->entries[i];
        }
        /* The text here is only measured, when the menu opens; Mod_DrawMenuRow draws
         * the entry's own. */
        state->entries[i].text = def->entries[0].text;
        state->entries[i].unk02 = 0;
        state->entries[i].result = MENU_RESULT_TRAINER;
        state->entries[i].centred = 0;
        state->menu.count = def->count + 1;
        state->menu.entries = state->entries;
        state->minWidth = def->marginLeft + Text_Width(def->font, def->fontArg + 2, sChangeTrainer) +
                          def->marginRight;
    }
    return &state->menu;
}

/* The window starts from what the player has now: the remembered picture and title, and
 * the name their team has, their own or a Game Pak's. */
static void Trainer_Open(TrainerState *state, Menu *menu, s32 controller) {
    u8 *entry = Trainer_EntryState(menu);
    char *name = (char *)entry + ENTRY_STATE_PARTY + PARTY_NAME;
    s32 title;
    s32 i;

    state->open = TRUE;
    state->typing = FALSE;
    state->owner = menu;
    state->controller = controller;
    state->port = Trainer_SidePort(entry);
    state->row = TRAINER_PICTURE;
    state->repeatTimer = 0;
    state->bracketPhase = 0;

    state->choice = gTrainerChoices[state->port];
    if (state->choice > NUM_TRAINER_PICTURES) {
        state->choice = 0;
    }
    title = gTrainerTitles[state->port] ^ PLAYER_TRAINER_TITLE;
    state->title = 0;
    for (i = 0; i < NUM_TITLES; i++) {
        if (sTrainerTitles[i] == title) {
            state->title = i;
        }
    }
    for (i = 0; i < MAX_TRAINER_NAME && name[i] != '\0'; i++) {
        state->name[i] = name[i];
    }
    state->name[i] = '\0';
    state->nameChanged = FALSE;

    Trainer_LoadPicture(state);
    Trainer_LoadTitle(state);
}

/* A keeps everything the window shows: for the screens to come, and, for the name, on
 * the team being chosen, which is where the game takes it from. */
static void Trainer_Keep(TrainerState *state) {
    char *remembered = gTrainerNames + state->port * TRAINER_NAME_BYTES;
    s32 i;

    gTrainerChoices[state->port] = state->choice;
    gTrainerTitles[state->port] = sTrainerTitles[state->title] ^ PLAYER_TRAINER_TITLE;
    if (state->nameChanged) {
        for (i = 0; i < TRAINER_NAME_BYTES; i++) {
            remembered[i] = state->name[i];
        }
        HAL_Strcpy((char *)Trainer_EntryState(state->owner) + ENTRY_STATE_PARTY + PARTY_NAME, state->name);
    }
}

/* A step round a ring of `count` choices. */
static s32 Trainer_Step(s32 value, s32 step, s32 count) {
    value += step;
    if (value < 0) {
        return count - 1;
    }
    return value < count ? value : 0;
}

static void Trainer_Update(TrainerState *state, Pad *pad) {
    EditState *keyboard = Edit_GetState();
    s32 buttons;
    s32 step = 0;
    s32 status;
    s32 i;

    if (state->typing) {
        status = Edit_UpdateKeyboard(keyboard, pad);
        if (status == KEYBOARD_DONE) {
            for (i = 0; i < TRAINER_NAME_BYTES; i++) {
                state->name[i] = i < MAX_TRAINER_NAME ? keyboard->name[i] : '\0';
            }
            state->nameChanged = TRUE;
        }
        state->typing = status == KEYBOARD_TYPING;
        return;
    }

    buttons = Edit_RepeatedButtons(&state->repeatTimer, pad, BTN_DLEFT | BTN_DRIGHT);
    if (pad->pressed & BTN_B) {
        Sound_Play(SOUND_CANCEL);
        state->open = FALSE;
        return;
    }
    if (pad->pressed & BTN_A) {
        Sound_Play(SOUND_CONFIRM);
        if (state->row == TRAINER_NAME) {
            Edit_OpenKeyboard(keyboard, state->name, MAX_TRAINER_NAME);
            state->typing = TRUE;
        } else {
            Trainer_Keep(state);
            state->open = FALSE;
        }
        return;
    }
    if (pad->pressed & BTN_DUP) {
        state->row = Trainer_Step(state->row, -1, NUM_TRAINER_ROWS);
        Sound_Play(SOUND_CURSOR);
        return;
    }
    if (pad->pressed & BTN_DDOWN) {
        state->row = Trainer_Step(state->row, 1, NUM_TRAINER_ROWS);
        Sound_Play(SOUND_CURSOR);
        return;
    }

    if (buttons & BTN_DRIGHT) {
        step = 1;
    } else if (buttons & BTN_DLEFT) {
        step = -1;
    }
    if (step == 0 || state->row == TRAINER_NAME) {
        return;
    }
    /* The pictures run in a ring, the game's own and then every trainer; the titles
     * likewise, the player's own first. */
    if (state->row == TRAINER_PICTURE) {
        state->choice = Trainer_Step(state->choice, step, NUM_TRAINER_PICTURES + 1);
        Trainer_LoadPicture(state);
    } else {
        state->title = Trainer_Step(state->title, step, NUM_TITLES);
        Trainer_LoadTitle(state);
    }
    Sound_Play(SOUND_CURSOR);
}

/**
 * Stands in for func_81311C70 where func_81303648 asks the team menu for its result,
 * once a frame while a team is chosen and awaits OK. The menu it is given has "Change
 * Trainer" added; choosing that opens the trainer window, which then gets the input
 * until it closes, and the menu comes back the frame after.
 */
s32 Mod_PollTeamMenu(Menu *menu, MenuDef *def, s32 controller, s32 textArg) {
    TrainerState *state = Trainer_GetState();
    s32 result = 0;

    if (state->open) {
        Trainer_Update(state, &gPads[state->controller]);
    } else {
        def = Trainer_ExtendMenu(state, menu, def);
        result = Menu_Poll(menu, def, controller, textArg);
        if (def == &state->menu && menu->def == def && menu->width < state->minWidth) {
            menu->x -= (state->minWidth - menu->width) / 2;
            menu->width = state->minWidth;
        }
        if (result == MENU_RESULT_TRAINER) {
            Trainer_Open(state, menu, controller);
            result = 0;
        }
    }
    if (state->open && state->typing) {
        Region_Add(gUiContext, KEYBOARD_REGION_KEY, TRUE, EDIT_WINDOW_X, EDIT_WINDOW_Y, EDIT_WINDOW_WIDTH,
                   EDIT_WINDOW_HEIGHT);
    } else if (state->open) {
        Region_Add(gUiContext, TRAINER_REGION_KEY, TRUE, WINDOW_X, WINDOW_Y, WINDOW_WIDTH, WINDOW_HEIGHT);
    }
    return result;
}

/**
 * Replaces func_81302EE4, which sets up the team a side is about to choose and gives it
 * a name: a Game Pak's trainer name, or none. A player who has typed a name gets that.
 */
void Mod_PartyInit(u8 *party, u8 *state, char *name, s32 id, void *arg4, void *arg5) {
    s32 port = Trainer_SidePort(state);

    if (port >= 0 && gTrainerNames[port * TRAINER_NAME_BYTES] != '\0') {
        name = gTrainerNames + port * TRAINER_NAME_BYTES;
    }
    orig_func_81302EE4(party, state, name, id, arg4, arg5);
}

/**
 * Replaces func_813114B8, which draws one entry of a popup menu from its text bank.
 * "Change Trainer" is in no text bank, so it is drawn here the way the stock function
 * draws the rest.
 */
void Mod_DrawMenuRow(Menu *menu, s32 row) {
    TrainerState *state = Trainer_GetState();
    MenuDef *def = menu->def;

    if (def != &state->menu || row != def->count - 1) {
        orig_func_813114B8(menu, row);
        return;
    }
    if (menu->highlight && row == menu->cursor) {
        Text_SetColor(0xFF, 0xFF, 0, 0xFF);
    } else {
        Text_SetColor(0xFF, 0xFF, 0xFF, 0xFF);
    }
    Text_SetFont(def->font, def->fontArg + 2);
    Text_Draw(menu->x + def->marginLeft, menu->y + def->marginTop + def->rowSpacing * row, sChangeTrainer);
}

/* Writes `value` in decimal ending at `end`, and returns where it starts. */
static char *Trainer_Digits(char *end, s32 value) {
    *end = '\0';
    do {
        *--end = '0' + value % 10;
        value /= 10;
    } while (value != 0);
    return end;
}

static void Trainer_DrawCentred(s32 y, char *str) {
    Text_Draw(WINDOW_X + (WINDOW_WIDTH - Text_Width(MENU_FONT, 1, str)) / 2, WINDOW_Y + y, str);
}

/* The name as the window shows it: the one typed, or failing that what the game will
 * call the player. */
static char *Trainer_ShownName(TrainerState *state) {
    if (state->name[0] != '\0') {
        return state->name;
    }
    return Text_Lookup(ENTRY_TEXT_BANK, ENTRY_TEXT_PLAYER + state->port);
}

static void Trainer_RowColor(TrainerState *state, s32 row) {
    if (state->row == row) {
        Text_SetColor(0xFF, 0xFF, 0, 0xFF);
    } else {
        Text_SetColor(0xFF, 0xFF, 0xFF, 0xFF);
    }
}

static void Trainer_DrawWindow(TrainerState *state) {
    s32 x = WINDOW_X;
    s32 y = WINDOW_Y;
    char *name = Trainer_ShownName(state);
    char *title = state->titleText + state->titleStart;
    char buffer[12];
    char *number;
    s32 middle = x + PICTURE_X + TRAINER_PICTURE_SIZE / 2;

    Window_Draw(x, y, WINDOW_WIDTH, WINDOW_HEIGHT);
    /* The cursor: the stock brackets, around whichever of the three it is on. */
    if (state->row == TRAINER_PICTURE) {
        Brackets_Draw(x + PICTURE_X - PICTURE_MARGIN, y + PICTURE_Y - PICTURE_MARGIN,
                      TRAINER_PICTURE_SIZE + 2 * PICTURE_MARGIN, TRAINER_PICTURE_SIZE + 2 * PICTURE_MARGIN,
                      &state->bracketPhase, 0xF0, 0xD4, 0x68, TRUE);
    } else if (state->row == TRAINER_NAME) {
        Brackets_Draw(x + VALUE_X - FIELD_MARGIN, y + NAME_Y - FIELD_RISE,
                      Text_Width(MENU_FONT, 1, name) + 2 * FIELD_MARGIN, FIELD_HEIGHT, &state->bracketPhase, 0xF0,
                      0xD4, 0x68, TRUE);
    } else {
        Brackets_Draw(x + VALUE_X - FIELD_MARGIN, y + TITLE_ROW_Y - FIELD_RISE,
                      Text_Width(MENU_FONT, 1, title) + 2 * FIELD_MARGIN, FIELD_HEIGHT, &state->bracketPhase, 0xF0,
                      0xD4, 0x68, TRUE);
    }
    gSPDisplayList(gDisplayListHead++, D_80094E38);
    Image_Draw(x + PICTURE_X, y + PICTURE_Y, state->picture, 0, 0);

    gSPDisplayList(gDisplayListHead++, D_80094F50);
    Text_Begin();
    Text_SetFont(MENU_FONT, 1);
    Text_SetColor(0x80, 0xE0, 0xFF, 0xFF);
    Trainer_DrawCentred(TITLE_Y, sHeading);
    Text_Draw(x + LABEL_X, y + NAME_Y, sName);
    Text_Draw(x + LABEL_X, y + TITLE_ROW_Y, sTitle);

    /* The picture's place in its ring, e.g. 12/68, around a slash under its middle. */
    Trainer_RowColor(state, TRAINER_PICTURE);
    number = Trainer_Digits(&buffer[11], state->choice + 1);
    Text_Draw(middle - 3 - Text_Width(MENU_FONT, 1, number), y + COUNT_Y, number);
    Text_Draw(middle - 3, y + COUNT_Y, sSlash);
    Text_Draw(middle + 5, y + COUNT_Y, Trainer_Digits(&buffer[11], NUM_TRAINER_PICTURES + 1));

    /* A name the player has not given is the game's, in grey unless the cursor is on it. */
    if (state->row != TRAINER_NAME && state->name[0] == '\0') {
        Text_SetColor(0x90, 0x90, 0xA0, 0xFF);
    } else {
        Trainer_RowColor(state, TRAINER_NAME);
    }
    Text_Draw(x + VALUE_X, y + NAME_Y, name);
    Trainer_RowColor(state, TRAINER_TITLE);
    Text_Draw(x + VALUE_X, y + TITLE_ROW_Y, title);

    Text_SetColor(0xFF, 0xFF, 0xFF, 0xFF);
    Trainer_DrawCentred(HINT_Y, state->row == TRAINER_NAME ? sHintType : sHintChange);
    Trainer_DrawCentred(HINT_Y + HINT_SPACING, sHintMove);
    Text_End();
}

/**
 * Replaces func_81311650, which draws a popup menu. The trainer window stands in for the
 * team menu, and the keyboard for the window while a name is typed, so both are drawn
 * from the same call.
 */
void Mod_DrawMenu(Menu *menu, void *ctx) {
    TrainerState *state = Trainer_GetState();

    orig_func_81311650(menu, ctx);
    if (!state->open || menu != state->owner) {
        return;
    }
    if (state->typing) {
        if (Region_ShouldDraw(ctx, KEYBOARD_REGION_KEY)) {
            Edit_DrawKeyboard(Edit_GetState(), sName);
        }
    } else if (Region_ShouldDraw(ctx, TRAINER_REGION_KEY)) {
        Trainer_DrawWindow(state);
    }
}
