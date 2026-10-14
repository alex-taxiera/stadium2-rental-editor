"""What the mod assumes about the ROM where it lists every stage and rents every Pokemon
in a Free Battle, and the three rental Pokemon it adds. Run: python3 -m unittest discover mod/tests"""

import re
import struct
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_ROM = REPO_ROOT / "baseroms" / "us" / "baserom.z64"
GAME_H = REPO_ROOT / "mod" / "include" / "game.h"
EXTRA = REPO_ROOT / "mod" / "data" / "rental_extra.inc.c"
LEGAL_MOVES = REPO_ROOT / "mod" / "data" / "legal_moves.inc.c"
STOCK_PATCHES = REPO_ROOT / "mod" / "stock_patches.txt"
ASM_PATCHES = REPO_ROOT / "mod" / "asm_patches.txt"
STATE = REPO_ROOT / "mod" / "src" / "state.s"

MAIN_ROM, MAIN_VRAM = 0x1000, 0x80000400
RULE_SELECT_ROM, RULE_SELECT_VRAM = 0xB5DA0, 0x83100000   # fragment 6
PICKER_ROM, PICKER_VRAM = 0xF81B0, 0x81300020             # fragment 14's code
STAGE_LIST = "func_831000FC"
STAGE_FLAGS, NUM_STAGES = 0x831038E0, 30                  # D_831038E0: the save file's bit for each stage
RULE_RECORDS = 0x8009F828                                 # D_8009F828: the game's rule sets, by kind
ANYTHING_GOES, PRIME_CUP, PRIME_CUP_ROUND_2 = 5, 12, 13   # kinds
RULES_RENTALS, RULES_SPECIES = 0x3C, 0x14
RENTAL_ARCHIVE = 0x1708000
RENTAL_SIZE = 0x18
RIVAL_ROUND_2 = 60                                        # in the same archive: the Rival's team, as a roster
ROSTER_SIZE, ROSTER_TEAM = 0x98, 8
TEXT_ARCHIVE, MOVE_NAMES = 0x1D70000, 6
MEWTWO, MEW, LUGIA, HO_OH, CELEBI = 150, 151, 249, 250, 251
PIKACHU, PSYDUCK = 25, 54
ROUND_2_TABLE = 2                                         # the Prime Cup's rentals in Round 2

SLTI_AT_S0 = 0x2A010000   # slti $at, $s0, immediate
ADDIU_A2 = 0x24060000     # addiu $a2, $zero, immediate


def constant(name: str) -> int:
    """A #define of mod/include/game.h, a number or the name of another."""
    value = re.search(rf"^#define {name} (\w+)", GAME_H.read_text(encoding="utf-8"), re.M).group(1)
    return int(value, 0) if value[0].isdigit() else constant(value)


def patches(path: Path, function: str) -> dict:
    """Address -> the new instruction, for a function's lines of a patch file."""
    lines = re.findall(rf"^{function}\s+([0-9A-F]{{8}})\s+(.*?)\s*$", path.read_text(encoding="ascii"), re.M)
    return {int(address, 16): " ".join(instruction.split()) for address, instruction in lines}


def extra_rentals() -> list:
    """The mod's own rental records, as the bytes the compiler makes of them, and each one's comment."""
    text = EXTRA.read_text(encoding="ascii")
    body = text[text.index("static Rental sExtraRentals"):]
    found = []
    for comment, fields in re.findall(r"/\* (.*?) \*/\s*\{ (.*?) \},\n", body):
        level, species, item, unk, m1, m2, m3, m4, pp_ups, happiness, *rest = [
            int(number, 0) for number in re.findall(r"0x[0-9A-Fa-f]+|\d+", fields)]
        stat_exp, dvs, tail = rest[:5], rest[5], rest[6:]
        found.append((struct.pack(">10B5HH2B", level, species, item, unk, m1, m2, m3, m4, pp_ups, happiness,
                                  *stat_exp, dvs, *tail), comment))
    return found


@unittest.skipUnless(BASE_ROM.exists(), "no baserom; run tools/mod/check_rom.py")
class StagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = BASE_ROM.read_bytes()

    def word(self, address: int) -> int:
        return struct.unpack_from(">I", self.rom, address - RULE_SELECT_VRAM + RULE_SELECT_ROM)[0]

    def test_the_list_takes_the_first_three_stages_unasked_and_the_patch_takes_all(self):
        changed = patches(STOCK_PATCHES, STAGE_LIST)
        self.assertEqual(len(changed), 2)
        for address, instruction in changed.items():
            self.assertEqual(self.word(address), SLTI_AT_S0 | 3, f"{address:08X}")
            self.assertEqual(instruction, f"slti $at, $s0, 0x{NUM_STAGES:X}")

    def test_the_loop_goes_round_to_the_branch_on_that_test(self):
        first, second = sorted(patches(STOCK_PATCHES, STAGE_LIST))
        # bnez $at past the question to the save file, and a bnel back to it whose delay
        # slot is the second test: a loop of as many stages as the second counts to.
        self.assertEqual(self.word(first + 4) >> 16, 0x1420)
        self.assertEqual(self.word(second - 4) >> 16, 0x5613)
        target = second + ((self.word(second - 4) & 0xFFFF) - 0x10000) * 4
        self.assertEqual(target, first + 4)
        self.assertEqual(self.word(first - 4), 0x24130000 | NUM_STAGES)   # addiu $s3, $zero, 30

    def test_every_stage_has_a_bit_of_its_own(self):
        at = STAGE_FLAGS - RULE_SELECT_VRAM + RULE_SELECT_ROM
        flags = list(self.rom[at:at + NUM_STAGES])
        self.assertEqual(len(set(flags)), NUM_STAGES)
        self.assertEqual(sorted(flags), list(range(NUM_STAGES)))


@unittest.skipUnless(BASE_ROM.exists(), "no baserom; run tools/mod/check_rom.py")
class RentalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = BASE_ROM.read_bytes()

    def entry(self, number: int) -> int:
        """Where a table of the archive of rental Pokemon and rosters starts."""
        return RENTAL_ARCHIVE + struct.unpack_from(">I", self.rom, RENTAL_ARCHIVE + 0x10 + number * 0x10)[0]

    def table(self, number: int) -> list:
        at = self.entry(number)
        return [self.rom[at + 4 + i * RENTAL_SIZE:at + 4 + (i + 1) * RENTAL_SIZE] for i in range(self.rom[at])]

    def rules(self, kind: int) -> bytes:
        address, = struct.unpack_from(">I", self.rom, RULE_RECORDS - MAIN_VRAM + MAIN_ROM + kind * 4)
        return self.rom[address - MAIN_VRAM + MAIN_ROM:][:0x44]

    def move_name(self, move: int) -> str:
        offset, size = struct.unpack_from(">II", self.rom, TEXT_ARCHIVE + 0x10 + MOVE_NAMES * 0x10)
        bank = self.rom[TEXT_ARCHIVE + offset:TEXT_ARCHIVE + offset + size]
        start, = struct.unpack_from(">I", bank, 4 + (move - 1) * 4)
        return bank[start:bank.index(b"\0", start)].decode("ascii")

    def test_the_table_is_the_one_the_mod_names(self):
        for kind in (ANYTHING_GOES, PRIME_CUP):
            self.assertEqual(struct.unpack_from(">h", self.rules(kind), RULES_RENTALS)[0],
                             constant("RENTALS_PRIME_CUP"))
        self.assertEqual(struct.unpack_from(">h", self.rules(PRIME_CUP_ROUND_2), RULES_RENTALS)[0], ROUND_2_TABLE)

    def test_both_rule_sets_let_all_five_enter(self):
        for kind in (ANYTHING_GOES, PRIME_CUP):
            mask = self.rules(kind)[RULES_SPECIES:RULES_SPECIES + 0x20]
            for species in (MEWTWO, MEW, LUGIA, HO_OH, CELEBI):
                self.assertTrue(mask[(species - 1) >> 3] & (0x80 >> ((species - 1) & 7)), (kind, species))

    def test_round_twos_table_has_mew_and_celebi_and_other_moves_for_two(self):
        short, full = self.table(constant("RENTALS_PRIME_CUP")), self.table(ROUND_2_TABLE)
        for table in (short, full):
            species = [record[1] for record in table]
            self.assertEqual(species, sorted(species))
        self.assertEqual(sorted(set(range(1, 252)) - {record[1] for record in short}),
                         [MEWTWO, MEW, LUGIA, HO_OH, CELEBI])
        self.assertEqual(sorted(set(range(1, 252)) - {record[1] for record in full}), [MEWTWO, LUGIA, HO_OH])
        # Which is why the mod has those two and not that table whole: Pikachu and
        # Psyduck are not as a Free Battle has them.
        theirs = {record[1]: record for record in full}
        self.assertEqual([record[1] for record in short if record != theirs[record[1]]], [PIKACHU, PSYDUCK])

    def test_the_mods_five_are_the_five_a_free_battle_has_no_rental_of(self):
        records = [record for record, _ in extra_rentals()]
        self.assertEqual([record[1] for record in records], [MEWTWO, MEW, LUGIA, HO_OH, CELEBI])
        self.assertIn(f"#define NUM_EXTRA_RENTALS {len(records)}\n", EXTRA.read_text(encoding="ascii"))
        for record in records:
            self.assertEqual(len(record), RENTAL_SIZE)

    def test_mew_and_celebi_are_the_games_own(self):
        full = {record[1]: record for record in self.table(ROUND_2_TABLE)}
        ours = {record[1]: record for record, _ in extra_rentals()}
        for species in (MEW, CELEBI):
            self.assertEqual(ours[species], full[species])

    def test_the_other_three_have_the_stats_the_game_gives_those_two(self):
        full = {record[1]: record for record in self.table(ROUND_2_TABLE)}

        def stats(record: bytes) -> bytes:
            # Level, no item, no PP Ups, happiness, Stat Exp and DVs: all but the species and the moves.
            return record[:1] + record[2:4] + record[8:]

        self.assertEqual(stats(full[MEW]), stats(full[CELEBI]))
        for record, _ in extra_rentals():
            self.assertEqual(stats(record), stats(full[MEW]))

    def test_the_other_three_have_the_moves_of_the_rivals_own_in_round_two(self):
        team = self.entry(RIVAL_ROUND_2) + 4 + ROSTER_TEAM
        rival = {}
        for i in range(6):
            record = self.rom[team + i * RENTAL_SIZE:team + (i + 1) * RENTAL_SIZE]
            rival[record[1]] = record
        for record, _ in extra_rentals():
            if record[1] in (MEWTWO, LUGIA, HO_OH):
                self.assertEqual(rival[record[1]][0], 100)
                self.assertEqual(record[4:8], rival[record[1]][4:8])

    def test_the_comments_name_the_moves_as_the_game_does(self):
        for record, comment in extra_rentals():
            named = comment.split(": ")[1].upper().replace(" ", "").split(",")
            self.assertEqual(named, [self.move_name(move).replace(" ", "") for move in record[4:8]])

    def test_every_move_of_theirs_is_one_the_editor_offers(self):
        rows = re.findall(r"^\s*\{ (0x[0-9A-F, x]+) \},", LEGAL_MOVES.read_text(encoding="utf-8"), re.M)
        legal = [[]] + [[int(byte, 16) for byte in row.split(", ")] for row in rows]
        self.assertEqual(len(legal), 252)
        for record, _ in extra_rentals():
            for move in record[4:8]:
                self.assertTrue((legal[record[1]][move >> 3] >> (move & 7)) & 1, (record[1], move))

    def test_the_picker_has_room_for_every_pokemon(self):
        # func_81307D08 gives the last source of the list, the rentals, five arrays this
        # far apart, and the others, a Game Pak's boxes, 0x1E.
        at = 0x81307D44 - PICKER_VRAM + PICKER_ROM
        self.assertEqual(struct.unpack_from(">I", self.rom, at)[0], ADDIU_A2 | 0xFE)
        self.assertLessEqual(constant("MAX_RENTALS"), 0xFE)
        self.assertEqual(constant("MAX_RENTALS"), 251)
        # The mod's table has that many records and a count before them.
        room = int(re.search(r"dlabel gRentalTable\n\s+\.space (\w+)", STATE.read_text(encoding="ascii")).group(1), 16)
        self.assertGreaterEqual(room, 4 + constant("MAX_RENTALS") * RENTAL_SIZE)

    def test_the_entry_screen_asks_the_mod_for_its_table(self):
        self.assertEqual(patches(ASM_PATCHES, "func_8130251C"), {0x813025B0: "jal Mod_RentalTable"})
        # jal func_80071B20, the game's own look-up of a table by its number.
        at = 0x813025B0 - PICKER_VRAM + PICKER_ROM
        self.assertEqual(struct.unpack_from(">I", self.rom, at)[0], 0x0C000000 | ((0x80071B20 & 0x0FFFFFFF) >> 2))


if __name__ == "__main__":
    unittest.main()
