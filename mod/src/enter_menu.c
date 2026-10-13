#include "edit.h"

static char sEditLabel[] = "EDIT";

/* The editor window's region is identified by the address of the editor's state. */
#define EDIT_REGION_KEY ((s32)Edit_GetState())

/**
 * Runs in place of func_8130251C, the entry screen's setup, as the mod is loaded. This is
 * the last moment the main pool has room to give, so the art the mod uses that the screen
 * does not load itself is loaded here.
 */
void Mod_EntrySetup(void) {
    Image_LoadBank(ARROW_IMAGES);
    orig_func_8130251C();
}

/**
 * Replaces func_8130DA04, which draws the ENTER menu (Yes / No / ITEM) beside the
 * detail panel. Adds an EDIT entry below the stock ones for rental Pokemon, and
 * draws the editor while it is open.
 */
void Mod_DrawEnterMenu(DetailPanel *panel, void *ctx) {
    s32 row;

    orig_func_8130DA04(panel, ctx);

    if (Edit_IsActive(panel)) {
        Edit_DrawSidebar(panel);
        if (Region_ShouldDraw(ctx, EDIT_REGION_KEY)) {
            Edit_DrawWindow(panel);
        }
        return;
    }
    if (panel->state != PANEL_MENU || !Edit_CanEdit(panel)) {
        return;
    }

    row = EnterMenu_StockCount(panel);
    gSPDisplayList(gDisplayListHead++, D_80094F50);
    Text_Begin();
    Text_SetFont(MENU_FONT, 1);
    if (panel->cursor == row) {
        Text_SetColor(0xFF, 0xFF, 0, 0xFF);
    } else {
        Text_SetColor(0xFF, 0xFF, 0xFF, 0xFF);
    }
    Text_Draw(panel->x + ENTER_MENU_X + ENTER_MENU_ITEM_X,
              panel->y + ENTER_MENU_ITEM_Y + ENTER_MENU_ITEM_SPACING * row, sEditLabel);
    Text_End();
}

/**
 * Replaces func_8130D1FC, which works out the ENTER menu's box as it opens and closes,
 * both to draw it and to register the screen region it covers, and makes it higher for
 * the ITEM list's "to quit". While the editor is open the box holds only its key hints,
 * so it is made lower, in step with how far open it is.
 */
f32 Mod_EnterMenuRect(DetailPanel *panel, Rect *rect) {
    f32 opening = orig_func_8130D1FC(panel, rect);

    if (Edit_IsActive(panel)) {
        rect->height = rect->height * EDIT_MENU_HEIGHT / ENTER_MENU_HEIGHT;
    }
    return opening;
}

/**
 * Replaces func_8130EC9C, the ENTER menu's input handler, which runs once a frame
 * while the menu is open. The stock handler never moves the cursor past its own last
 * entry, so stepping onto EDIT and choosing it are handled here. While the editor is
 * open it gets the input instead, and its window is registered as a screen region;
 * once that stops, the screen repaints what the window covered.
 */
void Mod_EnterMenuInput(DetailPanel *panel) {
    Pad *pad = &gPads[panel->controller];
    EditState *state = Edit_GetState();
    s32 editRow;

    if (Edit_IsActive(panel)) {
        Edit_Update(panel, pad);
    } else if (state->pending && panel->mode == PANEL_MODE_EXCHANGE) {
        /* Edit POKeMON: this is the one of the team it was chosen for, so the editor
         * opens in place of the EXCHANGE menu. Only a rental has one. */
        if (!Edit_CanEdit(panel)) {
            Sound_Play(SOUND_ERROR);
            Edit_ClosePanel(panel);
            return;
        }
        Edit_Open(panel, TRUE);
    } else {
        /* The stock menu, with EDIT on it. If Edit POKeMON was waiting, a panel of this
         * other kind means the team's box has been left, so it waits no more. */
        state->pending = FALSE;
        editRow = Edit_CanEdit(panel) ? EnterMenu_StockCount(panel) : -1;
        if (editRow >= 0 && panel->cursor == editRow && (pad->pressed & BTN_A)) {
            Sound_Play(SOUND_CONFIRM);
            Edit_Open(panel, FALSE);
        } else if (editRow >= 0 && panel->cursor == editRow - 1 && (pad->pressed & BTN_DDOWN) &&
                   !(pad->pressed & (BTN_A | BTN_B | BTN_DUP))) {
            Sound_Play(SOUND_CURSOR);
            panel->cursor = editRow;
            return;
        } else {
            orig_func_8130EC9C(panel);
            return;
        }
    }

    if (Edit_IsActive(panel)) {
        Region_Add(gUiContext, EDIT_REGION_KEY, TRUE, EDIT_WINDOW_X, EDIT_WINDOW_Y, EDIT_WINDOW_WIDTH,
                   EDIT_WINDOW_HEIGHT);
    }
}
