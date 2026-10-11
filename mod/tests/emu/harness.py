"""Shared by the emulator tests: one BizHawk at a time, and how to read the game through it.

Every test starts from a savestate made earlier in the same run, so tests do not depend
on each other or on anything left over from before: the console is switched on with no
save data, walked to the map, and each scene (a screen a group of tests starts on) is
reached from there once and saved.

Checks read game memory. Addresses and layouts below come from mod/NOTES.md and
mod/include; the editor's own state is found through the mod's ELF.
"""

import atexit
import re
import struct
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import emu  # noqa: E402
import fragment_relocs as fr  # noqa: E402
from check_rom import HOLE_START  # noqa: E402

TEST_DIR = REPO_ROOT / ".emu" / "test"
ROM = REPO_ROOT / "build" / "pokestadiumgs-us-mod.z64"
ROM_4MB = REPO_ROOT / "build" / "pokestadiumgs-us-mod-4mb.z64"
MOD_ELF = REPO_ROOT / "build" / "mod" / "mod.elf"
BASE_ROM = REPO_ROOT / "baseroms" / "us" / "baserom.z64"

MISSING = [str(p.relative_to(REPO_ROOT)) for p in (emu.EMUHAWK, ROM, ROM_4MB, MOD_ELF, BASE_ROM) if not p.exists()]
AVAILABLE = sys.platform == "win32" and not MISSING
SKIP_REASON = ("needs Windows" if sys.platform != "win32" else
               "missing " + ", ".join(MISSING) + "; build with tools/mod/wsl_build.sh mod")

# --- the game ---------------------------------------------------------------------------

FRAGMENT_MAP = 0x800CC630      # D_800CC630: {base, size} for each fragment id
MOD_VRAM = 0x85000000
PICKER_VRAM = 0x81300000       # fragment 14, the entry screen and rental picker
PICKER_STATE = 0x81317800      # D_81317800
PARTY_CELL = 0x15390           # in the picker's state: the first Pokemon entered
BATTLE_RECORD = 0x800D1C60     # player 1's first Pokemon during a battle
POOL_FREE = 0x800CCDCC         # bytes free in the main pool
RAM_SIZE = 0x800871F4          # D_800871F4
MAIN_ROM, MAIN_VRAM = 0x1000, 0x80000400   # where the main segment sits in the ROM and in RAM

BASE_STATS = 0x8009830B        # per species, 22 bytes: HP, Attack, Defense, Speed, Sp. Atk, Sp. Def at +0
MOVE_PP = 0x8009782E           # per move, 6 bytes: base PP at +0

RECORD_SIZE = 0x58
CELL_ICON, ICON_SIZE = 0x60, 0xC88   # a list cell is a record followed by, among other things, its icon

ABRA, PSYCHIC, ICE_PUNCH, HIDDEN_POWER = 63, 94, 8, 237


def fragment_id(vram: int) -> int:
    return ((vram & 0x0FF00000) >> 20) - 0x10


def rom_bytes(address: int, length: int) -> bytes:
    """Main-segment data straight from the original ROM, for expected values."""
    with BASE_ROM.open("rb") as f:
        f.seek(address - MAIN_VRAM + MAIN_ROM)
        return f.read(length)


def base_stats(species: int) -> list:
    return list(rom_bytes(BASE_STATS + species * 22, 6))


def base_pp(move: int) -> int:
    return rom_bytes(MOVE_PP + move * 6, 1)[0]


def stat_exp_term(stat_exp: int) -> int:
    """floor(ceil(sqrt(stat_exp)) / 4), the Game Boy way: the root is capped at 255."""
    root = 0
    while root * root < stat_exp and root < 255:
        root += 1
    return root // 4


def expected_stats(species: int, level: int, dvs: int, stat_exp: list) -> list:
    """Max HP, Attack, Defense, Speed, Sp. Atk, Sp. Def by the Generation 2 formula."""
    attack, defense, speed, special = (dvs >> 12) & 15, (dvs >> 8) & 15, (dvs >> 4) & 15, dvs & 15
    hp = ((attack & 1) << 3) | ((defense & 1) << 2) | ((speed & 1) << 1) | (special & 1)
    base = base_stats(species)
    # Both special stats use the Special DV and the Special Stat Exp.
    inputs = [(base[0], hp, stat_exp[0]), (base[1], attack, stat_exp[1]), (base[2], defense, stat_exp[2]),
              (base[3], speed, stat_exp[3]), (base[4], special, stat_exp[4]), (base[5], special, stat_exp[4])]
    stats = [((b + dv) * 2 + stat_exp_term(exp)) * level // 100 + 5 for b, dv, exp in inputs]
    stats[0] += level + 5
    return stats


def medium_slow_exp(level: int) -> int:
    """Experience at a level on the Medium Slow curve, which Abra uses."""
    return 6 * level ** 3 // 5 - 15 * level ** 2 + 100 * level - 140


def legal_moves(species: int) -> list:
    """The species' legal moves in the order the editor lists them, from the generated table."""
    text = (REPO_ROOT / "mod" / "data" / "legal_moves.inc.c").read_text(encoding="ascii")
    table, order = text.split("static const u8 sMoveOrder")
    rows = re.findall(r"^    \{ (.*?) \}", table, re.M)
    row = [int(v, 16) for v in rows[species].split(", ")] if rows[species] != "0" else [0] * 32
    order = [int(v) for v in re.findall(r"\d+", order.split("{", 1)[1])]
    return [move for move in order if row[move >> 3] >> (move & 7) & 1]


class Record:
    """A Pokemon record, 0x58 bytes; see `Pokemon` in mod/include/game.h."""

    def __init__(self, data: bytes):
        self.data = bytes(data[:RECORD_SIZE])
        d = self.data
        self.species, self.item = d[0], d[1]
        self.moves = list(d[2:6])
        self.exp, = struct.unpack_from(">I", d, 0x08)
        self.stat_exp = list(struct.unpack_from(">5H", d, 0x0C))
        self.dvs, = struct.unpack_from(">H", d, 0x16)
        self.pp = list(d[0x18:0x1C])
        self.level, self.flags = d[0x1D], d[0x1E]
        self.hp, = struct.unpack_from(">H", d, 0x26)
        self.stats = list(struct.unpack_from(">6H", d, 0x28))
        self.nickname = d[0x34:0x40].split(b"\0")[0]

    @property
    def editable(self) -> bytes:
        """Everything the editor can change, plus what follows from it."""
        return self.data[:0x40]


class EditState:
    """The editor's state; see `EditState` in mod/include/edit.h."""

    SIZE = 0x164
    OFF, FIELDS, ADJUST, MOVE_LIST, NAME = range(5)
    COL_MOVES, COL_DV, COL_STAT_EXP = range(3)

    def __init__(self, data: bytes):
        self.mode, self.col, self.row = data[0], data[1], data[2]
        self.count, self.cursor, self.top = struct.unpack_from(">3h", data, 4)
        self.on_name, self.key_page = data[0x0A], data[0x0B]
        self.panel, = struct.unpack_from(">I", data, 0x0C)
        self.list = list(data[0x10:0x10 + max(self.count, 0)])
        self.key_col, self.key_row, self.name_length = data[0x10C], data[0x10D], data[0x10E]
        self.name = data[0x110:0x11B].split(b"\0")[0]


class Panel:
    """The detail panel; see `DetailPanel` in mod/include/game.h."""

    SIZE = 0x74
    CLOSED, MENU = 0, 1

    def __init__(self, data: bytes):
        self.redraw, = struct.unpack_from(">i", data, 0x00)
        self.state, self.mode, self.controller = data[0x34], data[0x35], data[0x37]
        self.cursor, = struct.unpack_from(">b", data, 0x36)
        self.item = data[0x39]
        self.item_list, = struct.unpack_from(">I", data, 0x5C)
        self.model, self.pokemon, self.model_timer = struct.unpack_from(">IIi", data, 0x68)


class ItemList:
    """The ENTER menu's ITEM list: "No item" alone on the top row, then two items a row.
    The cursor is on entry (top + row) * 2 + column - 1."""

    SIZE = 0x8C

    def __init__(self, data: bytes):
        self.column, self.row = struct.unpack_from(">2h", data, 0x08)
        count, = struct.unpack_from(">H", data, 0x50)
        self.items = list(data[0x10:0x10 + count])
        self.top, = struct.unpack_from(">h", data, 0x7C)
        self.state = data[0x87]


# --- input ------------------------------------------------------------------------------

UP, DOWN, LEFT, RIGHT = "DPad U", "DPad D", "DPad L", "DPad R"


def press(button: str, wait: int = 10, frames: int = 4) -> list:
    """Commands to press a button and let the game act on it."""
    return [f"press {button} {frames}", f"wait {wait}"]


def presses(button: str, count: int, wait: int = 10) -> list:
    return press(button, wait) * count


# Switch-on to the map, with nothing saved on the cartridge.
BOOT = (["wait 600"] + press("Start", 240, 6) + press("Start", 300, 6) + press("A", 300, 6) + press("A", 400, 6))
# Map to Free Battle's set-up screen.
FREE_BATTLE = press(RIGHT, 40, 6) + press(UP, 40, 6) + press("A", 300, 6)
# On an entry screen: Rental Only, which opens the picker.
RENTAL_ONLY = press(RIGHT, 20, 6) + press(RIGHT, 20, 6) + press("A", 300, 6)
# In the picker: enter the first rental as it is and confirm the team.
ENTER_FIRST = press("A", 60) + press("A", 90) + press("Start", 60) + press("A", 240)

SCENES = {
    # 1P vs COM, Anything Goes, in the rental picker.
    "picker": FREE_BATTLE + presses("A", 3, 40) + press("A", 120, 6) + press("A", 120, 6) + press("A", 300, 6)
              + RENTAL_ONLY,
    # The same under Poke Cup rules (levels 50 to 55).
    "cup": FREE_BATTLE + presses("A", 3, 40) + press("A", 60, 6) + presses(DOWN, 2, 20) + press("A", 120, 6)
           + press("A", 300, 6) + RENTAL_ONLY,
    # 1P vs 2P: player 1 has entered a rental, and player 2 is in the picker. (Against a
    # person there is no difficulty to choose, so this takes one press fewer.)
    "two": FREE_BATTLE + press("A", 40, 6) + press(DOWN, 20, 6) + press("A", 40, 6) + press("A", 120, 6)
           + press("A", 300, 6) + RENTAL_ONLY + ENTER_FIRST
           + ["player 2"] + RENTAL_ONLY + ["player 1"],
}

# In the picker: open the first rental (Abra) and choose EDIT.
OPEN_PANEL = press("A", 60)
OPEN_EDITOR = OPEN_PANEL + presses(DOWN, 3) + press("A", 30)


class Session:
    """A running game. `scene` returns the commands that put a test at its starting point."""

    def __init__(self, rom: Path):
        self.rom = rom
        self.dir = TEST_DIR / "remote"
        config = emu.make_config(emu.BIZHAWK / "config.ini", TEST_DIR / "config.ini", controllers=2)
        self.emulator = emu.Emulator(self.dir, config, stepping=True)
        self.emulator.start(emu.fresh_rom(rom, "s2-test.z64", TEST_DIR))
        # The game ran for a moment before the script took hold of it. Switch it off and
        # on, so that every run counts its frames from the same place.
        self.emulator.reboot()
        if self.run("frame") != ["frame 0"]:
            raise emu.EmulatorError("the game did not restart at frame 0")
        self.saved = set()
        self.run("turbo on", *BOOT, "save map")
        header = fr.read_header(rom.read_bytes(), HOLE_START)
        self.mod_size = header.size_in_ram
        self.state_offset = fr.Elf(MOD_ELF).symbol("gEditState") - MOD_VRAM

    def run(self, *commands: str, timeout: float = 300) -> list:
        output = self.emulator.run(*commands, timeout=timeout)
        errors = [line for line in output if line.startswith(("error in", "unknown command"))]
        if errors:
            raise emu.EmulatorError("; ".join(errors))
        return output

    def scene(self, name: str) -> list:
        if name not in self.saved:
            self.run("player 1", "load map", "wait 20", *SCENES[name], f"save {name}")
            self.saved.add(name)
        return ["player 1", f"load {name}", "wait 4"]

    def reboot(self) -> None:
        """Switches the console off and on, and walks back to the map."""
        self.emulator.reboot()
        self.run("turbo on", *BOOT)

    # --- reading the game -----------------------------------------------------------

    def read(self, address: int, length: int) -> bytes:
        data = bytearray()
        for line in self.run(f"read {address:08X} {length}"):
            data += bytes.fromhex(line.split(":", 1)[1])
        return bytes(data)

    def u32(self, address: int) -> int:
        return int(self.run(f"u32 {address:08X}")[0], 16)

    def find(self, needle: bytes) -> list:
        """Addresses of every copy of `needle` in memory."""
        return [int(line, 16) for line in self.run("find " + needle.hex()) if re.fullmatch(r"[0-9A-F]{8}", line)]

    def fragment(self, vram: int) -> tuple:
        """(base, size) of a loaded fragment, or (0, 0)."""
        return struct.unpack(">II", self.read(FRAGMENT_MAP + fragment_id(vram) * 8, 8))

    def edit_state(self) -> EditState:
        base, _ = self.fragment(MOD_VRAM)
        if base == 0:
            raise AssertionError("the mod is not loaded")
        return EditState(self.read(base + self.state_offset, EditState.SIZE))

    def panel(self, state: EditState = None) -> Panel:
        state = state or self.edit_state()
        if state.panel == 0:
            raise AssertionError("the editor has not been opened")
        return Panel(self.read(state.panel, Panel.SIZE))

    def record(self) -> Record:
        """The Pokemon open in the editor."""
        return Record(self.read(self.panel().pokemon, RECORD_SIZE))

    def party(self, index: int = 0) -> Record:
        """A Pokemon entered in the picker."""
        base, _ = self.fragment(PICKER_VRAM)
        return Record(self.read(base + PICKER_STATE - PICKER_VRAM + PARTY_CELL + index * 0xCE8, RECORD_SIZE))

    def shot(self, name: str) -> Path:
        """A screenshot at normal speed, so the picture is of the frame just emulated."""
        self.run("turbo off", "wait 2", f"shot {name}", "turbo on")
        return self.dir / f"{name}.png"

    def stop(self) -> None:
        self.emulator.stop()


class EmulatorTest(unittest.TestCase):
    """A group of tests that start from one scene of one ROM."""

    rom = ROM
    scene = "picker"

    @classmethod
    def setUpClass(cls):
        cls.s = session(cls.rom)

    def start(self, *commands: str) -> None:
        """Puts the game at the scene, then runs commands."""
        self.s.run(*self.s.scene(self.scene), *commands)

    def do(self, *commands: str) -> None:
        self.s.run(*commands)

    def assertStatsFollow(self, record: Record) -> None:
        """The record's stats are what its level, DVs and Stat Exp give by the formula."""
        self.assertEqual(record.stats, expected_stats(record.species, record.level, record.dvs, record.stat_exp))
        self.assertEqual(record.hp, record.stats[0])


_current = None


def session(rom: Path = ROM) -> Session:
    """The running game for `rom`, starting it (and closing any other) if need be."""
    global _current
    if _current is None or _current.rom != rom:
        if _current is not None:
            _current.stop()
            _current = None
        _current = Session(rom)
    return _current


@atexit.register
def _stop() -> None:
    if _current is not None:
        _current.stop()
