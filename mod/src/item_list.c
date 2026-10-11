#include "game.h"

/**
 * Replaces func_81306B64, which sets up the ITEM list of the ENTER menu. The stock
 * screen offers six berries plus whatever a connected Game Pak owns, as a mask of item
 * ids. The list is given every item instead; building it (func_81602134) still keeps
 * only those the game classes as worth holding, so it comes out as it would for a Game
 * Pak that owned them all.
 */
void Mod_ItemListInit(void *list, s32 x, s32 y, s32 arg3, s32 *available) {
    s32 all[ITEM_MASK_WORDS];

    if (available != NULL) {
        ItemMask_Fill(all, TRUE);
        available = all;
    }
    orig_func_81306B64(list, x, y, arg3, available);
}
