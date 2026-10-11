#include "game.h"

static char sEditLabel[] = "EDIT";

/**
 * Replaces func_8130DA04, which draws the ENTER menu (Yes / No / ITEM) beside the
 * detail panel. Draws the stock menu, then an extra entry below it.
 */
void Mod_DrawEnterMenu(DetailPanel *panel, s32 arg1) {
    s32 x;
    s32 y;

    orig_func_8130DA04(panel, arg1);

    if (panel->state == PANEL_CLOSED || panel->mode != PANEL_MODE_ENTER) {
        return;
    }

    x = panel->x + ENTER_MENU_X + ENTER_MENU_ITEM_X;
    y = panel->y + ENTER_MENU_ITEM_Y + ENTER_MENU_ITEM_SPACING * 3;

    gSPDisplayList(gDisplayListHead++, D_80094F50);
    Text_Begin();
    Text_SetFont(4, 1);
    Text_SetColor(0xFF, 0xFF, 0xFF, 0xFF);
    Text_Draw(x, y, sEditLabel);
    Text_End();
}
