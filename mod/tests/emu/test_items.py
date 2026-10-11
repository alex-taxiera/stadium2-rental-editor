"""The ENTER menu's ITEM list, which the mod fills with every item worth holding.

Run on Windows from the repository root: python3 -m unittest discover -s mod/tests/emu
"""

import unittest

import harness as h
from harness import DOWN, ItemList, Panel, press, presses

HOLD_EFFECT = 0x80097FED   # per item, 3 bytes: what holding it does at +0
PANEL_ITEM_LIST = 4        # the panel's state while the list is open

# The stock list without a Game Pak: PRZCureBerry, Burnt, Ice, Bitter and Mint Berry, Berry.
STOCK = [0x4E, 0x4F, 0x50, 0x53, 0x54, 0xAD]
SPECIES_ONLY = [0x1E, 0x23, 0x69, 0x76, 0xA3]   # Lucky Punch, Metal Powder, Stick, Thick Club, Light Ball
NO_USE_IN_BATTLE = [0x5B, 0x5E, 0x6A]           # Amulet Coin, Cleanse Tag, Smoke Ball
LEFTOVERS, BERSERK_GENE = 0x92, 0x98

# The list is reached through the panel, and the panel through the editor's state, which
# knows it once the editor has been opened. So: into the editor, out, down to ITEM.
OPEN_LIST = h.OPEN_EDITOR + press("B", 30) + presses(DOWN, 2) + press("A", 40)


def expected_items() -> list:
    """What func_81602134 lists when every item is on offer: "No item", then the items
    in the order of the groups func_81601FA0 sorts them into."""
    effects = h.rom_bytes(HOLD_EFFECT, 0x100 * 3)[::3]

    def group(item: int) -> int:
        if item in STOCK:
            return 1
        if item in SPECIES_ONLY:
            return 5
        if item in NO_USE_IN_BATTLE:
            return 0
        if item in (LEFTOVERS, BERSERK_GENE):
            return 3
        effect = effects[item]
        if effect == 0:
            return 0
        if 0x32 <= effect < 0x43:   # the type boosts
            return 4
        return 2 if effect < 0x11 else 3

    return [0] + [item for wanted in range(1, 6) for item in range(1, 0xFF) if group(item) == wanted]


@unittest.skipUnless(h.AVAILABLE, h.SKIP_REASON)
class ItemListTest(h.EmulatorTest):
    def item_list(self) -> ItemList:
        return ItemList(self.s.read(self.s.panel().item_list, ItemList.SIZE))

    def test_list_offers_every_item_worth_holding(self):
        self.start(*OPEN_LIST)
        self.assertEqual(self.s.panel().state, PANEL_ITEM_LIST)
        items = self.item_list().items
        self.assertEqual(items, expected_items())
        self.assertEqual(len(items), 43)
        self.assertEqual(items[:7], [0] + STOCK)

    def test_an_item_from_beyond_the_stock_six_can_be_held(self):
        self.start(*OPEN_LIST)
        # The list opens on its first item; Leftovers is eight rows down, off the first page.
        self.do(*presses(DOWN, 8, 20))
        cursor = self.item_list()
        entry = (cursor.top + cursor.row) * 2 + cursor.column - 1
        self.assertEqual(cursor.items[entry], LEFTOVERS)

        # Choosing an item enters the Pokemon with it.
        self.do(*press("A", 80))
        panel = self.s.panel()
        self.assertEqual((panel.state, panel.item), (Panel.CLOSED, LEFTOVERS))
        party = self.s.party()
        self.assertEqual((party.species, party.item), (h.ABRA, LEFTOVERS))


if __name__ == "__main__":
    unittest.main()
