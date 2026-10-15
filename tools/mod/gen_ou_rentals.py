#!/usr/bin/env python3
"""Generate the rental Pokemon OU Rules gives in place of the game's own.

Every species Smogon has a GSC OU set for is rented with that set under the mod's OU
Rules: its moves, its item, its DVs and its Stat Exp, at level 100. The others keep the
game's record. See mod/src/rentals.c.

A species gets the first of its sets in Smogon's order that can be made, and each of
its move slots the first option that is

  * one the species can know in Generation 2, events included (Showdown's learnsets,
    as tools/mod/gen_legal_moves.py reads them), so Nidoking keeps Lovely Kiss,
    which EDIT does not offer;
  * not already in the set;
  * not kept out by a clause of OU Rules (mod/data/clause_moves.inc.c).

A set with no such option for a slot gives way to the next, and a species with no set
that can be made keeps the game's record (Ariados: its one set has Spider Web with
Baton Pass). The item is the first option the ENTER menu's ITEM list offers the
species, or none.

  * DVs are 15 unless the set says otherwise. Hidden Power's type is made with the
    attack and defense DVs, the highest that give it, and its power is then 70.
  * Stat Exp is the most there is unless the set says otherwise.
  * Happiness is 255 with Return, 0 with Frustration, and otherwise the 127 of the
    game's own level 100 records of Mew and Celebi. PP Ups are none: the picker does
    not read them (func_80071E48).

Inputs: pkmn/smogon's sets (MIT) and pret/pokecrystal's item ids, pinned by commit and
cached in mod/data/cache, with the Showdown data gen_legal_moves.py caches; and the
base ROM, for the moves' names as the game spells them in the comments and for which
items are worth holding. Standard library only.

    tools/mod/gen_ou_rentals.py --fetch     # download pinned data, then generate
    tools/mod/gen_ou_rentals.py             # regenerate from the cache
"""

import argparse
import json
import re
import struct
import sys
import urllib.request
from pathlib import Path

import gen_legal_moves as legal

# (GitHub repo, commit, path in repo, path in the cache directory)
SOURCES = {
    "sets": ("pkmn/smogon", "cd3738be653348ef3adf2015828ecd28c6eda241",
             "data/sets/gen2ou.json", "smogon/gen2ou.json"),
    "sets_license": ("pkmn/smogon", "cd3738be653348ef3adf2015828ecd28c6eda241",
                     "LICENSE", "smogon/LICENSE"),
    "items": ("pret/pokecrystal", "3bc8daa4173e96a7f4011dad3922eb6fa5dad5c6",
              "constants/item_constants.asm", "pret/crystal_item_constants.asm"),
}

REPO_ROOT = legal.REPO_ROOT
BASE_ROM = REPO_ROOT / "baseroms" / "us" / "baserom.z64"
CLAUSE_MOVES = REPO_ROOT / "mod" / "data" / "clause_moves.inc.c"
DEFAULT_CACHE = legal.DEFAULT_CACHE
DEFAULT_OUT = REPO_ROOT / "mod" / "data" / "rental_ou.inc.c"

LEVEL = 100
MAX_STAT_EXP = 0xFFFF
MAX_DV = 15
HAPPINESS, RETURN_HAPPINESS, FRUSTRATION_HAPPINESS = 127, 255, 0

HIDDEN_POWER = "hiddenpower"
HIDDEN_POWER_TYPES = ["Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel",
                      "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark"]

# Showdown's stats, in the order of a record's Stat Exp, and the DVs of each; special
# has one of each, and HP's DV is made of the other four.
STAT_EXP_ORDER = ["hp", "atk", "def", "spe", "spa"]
DV_ORDER = ["atk", "def", "spe", "spa"]

# The game's text of move names, as mod/tests/test_unlocks.py reads it.
TEXT_ARCHIVE, MOVE_NAMES = 0x1D70000, 6

# What holding an item does, three bytes an item (D_80097FED, in the main segment), and
# the items func_81601FA0 sorts apart from it; see mod/tests/emu/test_items.py.
MAIN_ROM, MAIN_VRAM = 0x1000, 0x80000400
HOLD_EFFECT = 0x80097FED
NO_USE_IN_BATTLE = {0x5B, 0x5E, 0x6A}           # Amulet Coin, Cleanse Tag, Smoke Ball
ALWAYS_HELD = {0x92, 0x98}                      # Leftovers, Berserk Gene
# The species items, which the list does not let another species take (func_81601D24).
SPECIES_ITEMS = {0x1E: {113}, 0x23: {132}, 0x69: {83}, 0x76: {104, 105}, 0xA3: {25}}

NO_ITEM = "noitem"
ITEM_CONSTANT = re.compile(r"^\tconst (\w+)\s*; ([0-9a-f]{2})$")


def cache_path(cache: Path, key: str) -> Path:
    return cache / SOURCES[key][3]


def fetch(cache: Path) -> None:
    for repo, commit, remote, local in SOURCES.values():
        url = f"https://raw.githubusercontent.com/{repo}/{commit}/{remote}"
        print(f"fetching {url}")
        dest = cache / local
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as r:
            dest.write_bytes(r.read())


def parse_items(path: Path) -> dict:
    """Item id (Showdown's spelling, as to_id makes it) -> number."""
    items = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ITEM_CONSTANT.match(line)
        if m:
            items[legal.to_id(m.group(1))] = int(m.group(2), 16)
    return items


def clause_moves(path: Path) -> tuple:
    """The moves no set may have, and the ones Baton Pass may not be with."""
    text = path.read_text(encoding="ascii")

    def array(name: str) -> set:
        body = re.search(rf"{name}\[\] = \{{(.*?)\}};", text, re.S).group(1)
        return {int(n) for n in re.findall(r"^\s*(\d+),", body, re.M)}

    baton_pass = int(re.search(r"#define MOVE_BATON_PASS (\d+)", text).group(1))
    return array("sEvasionMoves") | array("sOhkoMoves"), array("sTrappingMoves"), baton_pass


def move_names(rom: bytes) -> dict:
    """Move number -> its name as the game spells it."""
    offset, size = struct.unpack_from(">II", rom, TEXT_ARCHIVE + 0x10 + MOVE_NAMES * 0x10)
    bank = rom[TEXT_ARCHIVE + offset:TEXT_ARCHIVE + offset + size]
    names = {}
    for move in range(1, legal.NUM_MOVES + 1):
        start, = struct.unpack_from(">I", bank, 4 + (move - 1) * 4)
        names[move] = bank[start:bank.index(b"\0", start)].decode("ascii")
    return names


def offered_items(rom: bytes) -> set:
    """The items the ITEM list offers, when every item is on offer (Mod_ItemListInit)."""
    at = HOLD_EFFECT - MAIN_VRAM + MAIN_ROM
    effects = rom[at:at + 0x100 * 3][::3]
    return {item for item in range(1, 0xFF)
            if item not in NO_USE_IN_BATTLE and (effects[item] != 0 or item in ALWAYS_HELD
                                                 or item in SPECIES_ITEMS)}


def options(slot) -> list:
    return slot if isinstance(slot, list) else [slot]


def hidden_power_dvs(kind: int) -> tuple:
    """Attack and defense DVs for a Hidden Power of the type: the highest that give it."""
    atk = max(dv for dv in range(MAX_DV + 1) if dv % 4 == kind >> 2)
    defense = max(dv for dv in range(MAX_DV + 1) if dv % 4 == kind & 3)
    return atk, defense


def hidden_power(dvs: dict) -> tuple:
    """The type and power of Hidden Power with these DVs."""
    kind = (dvs["atk"] % 4) * 4 + dvs["def"] % 4
    bits = sum(weight for stat, weight in (("spa", 1), ("spe", 2), ("def", 4), ("atk", 8)) if dvs[stat] >= 8)
    return kind, (5 * bits + dvs["spa"] % 4) // 2 + 31


def stat_exp(ev: int) -> int:
    """The least Stat Exp that gives what Showdown's EVs do: a quarter of the EVs to the stat."""
    return MAX_STAT_EXP if ev >= 252 else (ev - 1) ** 2 + 1 if ev > 0 else 0


class Generator:
    def __init__(self, cache: Path, rom: bytes):
        data = legal.Data(cache)
        errors = data.validate()
        if errors:
            raise SystemExit("\n".join(f"error: {e}" for e in errors))
        self.moves = data.moves
        self.pokedex = data.pokedex
        self.legal = data.table(include_events=True)
        self.items = parse_items(cache_path(cache, "items"))
        self.sets = json.loads(cache_path(cache, "sets").read_text(encoding="utf-8"))
        self.refused, self.trapping, self.baton_pass = clause_moves(CLAUSE_MOVES)
        self.names = move_names(rom)
        self.offered = offered_items(rom)
        self.notes = []
        self.passed_over = []

    def species(self, name: str) -> int:
        return self.pokedex[legal.to_id(name)]["num"]

    def move_allowed(self, species: int, move: int, chosen: list) -> bool:
        if move not in self.legal[species] or move in chosen or move in self.refused:
            return False
        if move == self.baton_pass:
            return not self.trapping & set(chosen)
        return not (move in self.trapping and self.baton_pass in chosen)

    def item_allowed(self, species: int, item: int) -> bool:
        return item in self.offered and species in SPECIES_ITEMS.get(item, {species})

    def make(self, name: str, set_name: str, smogon: dict):
        """The record of one set, or None if it cannot be made."""
        species = self.species(name)
        chosen, hidden_power_type = [], None
        for slot in smogon["moves"]:
            for option in options(slot):
                move_id = legal.to_id(option)
                move = self.moves[move_id]
                if self.move_allowed(species, move, chosen):
                    chosen.append(move)
                    if move_id.startswith(HIDDEN_POWER) and move_id != HIDDEN_POWER:
                        hidden_power_type = HIDDEN_POWER_TYPES.index(option.split()[-1])
                    if option != options(slot)[0]:
                        self.notes.append(f"{name} ({set_name}): {option} in place of {options(slot)[0]}")
                    break
            else:
                self.notes.append(f"{name} ({set_name}): no option for {options(slot)} - set passed over")
                return None

        dvs = {stat: MAX_DV for stat in DV_ORDER}
        if hidden_power_type is not None:
            dvs["atk"], dvs["def"] = hidden_power_dvs(hidden_power_type)
        for stat, iv in smogon.get("ivs", {}).items():
            dvs[stat] = iv // 2
        if hidden_power_type is not None and hidden_power(dvs)[0] != hidden_power_type:
            raise SystemExit(f"error: {name} ({set_name}): its DVs do not give its Hidden Power")
        evs = smogon.get("evs", {})

        item_name, item = "", 0
        for option in options(smogon.get("item") or []):
            item_id = legal.to_id(option)
            if item_id == NO_ITEM:
                break
            if self.item_allowed(species, self.items[item_id]):
                item_name, item = option, self.items[item_id]
                break
            self.notes.append(f"{name} ({set_name}): {option} is not offered - passed over")

        happiness = HAPPINESS
        if self.moves["return"] in chosen:
            happiness = RETURN_HAPPINESS
        elif self.moves["frustration"] in chosen:
            happiness = FRUSTRATION_HAPPINESS

        return {
            "name": name, "set": set_name, "species": species, "item": item, "item_name": item_name,
            "moves": chosen + [0] * (4 - len(chosen)), "happiness": happiness,
            "stat_exp": [stat_exp(evs.get(stat, 252)) for stat in STAT_EXP_ORDER],
            "dvs": (dvs["atk"] << 12) | (dvs["def"] << 8) | (dvs["spe"] << 4) | dvs["spa"],
            "hidden_power": hidden_power_type,
        }

    def records(self) -> list:
        records = []
        for name, sets in self.sets.items():
            for set_name, smogon in sets.items():
                record = self.make(name, set_name, smogon)
                if record is not None:
                    records.append(record)
                    break
            else:
                self.passed_over.append(name)
        return sorted(records, key=lambda r: r["species"])

    def comment(self, record: dict) -> str:
        named = []
        for move in record["moves"]:
            if move:
                named.append(self.names[move])
        if record["hidden_power"] is not None:
            at = named.index(self.names[self.moves[HIDDEN_POWER]])
            named[at] += f" [{HIDDEN_POWER_TYPES[record['hidden_power']]}]"
        item = record["item_name"] or "no item"
        return f'{record["name"]}: {", ".join(named)} ({item}; Smogon\'s "{record["set"]}")'


def c_comment(text: str) -> str:
    return text.encode("ascii", "replace").decode().replace("*/", "* /")


def render(generator: Generator, records: list) -> str:
    sets = SOURCES["sets"]
    items = SOURCES["items"]
    out = [
        "// Generated by tools/mod/gen_ou_rentals.py. Do not edit by hand.",
        f"// Sources: Smogon's GSC OU sets from {sets[0]} @ {sets[1][:12]} (MIT);",
        f"// item numbers from {items[0]} @ {items[1][:12]}; move legality as legal_moves.inc.c,",
        "// with event moves; move names from the game.",
        "//",
        "// The rental Pokemon OU Rules gives in place of the game's own, one for every species",
        "// Smogon has a set for, in the order of their numbers. Level 100, DVs of 15 and the",
        "// most Stat Exp unless the set says otherwise. See mod/src/rentals.c.",
    ]
    if generator.passed_over:
        out.append(f"// No set of these can be made under OU Rules, which keep the game's own: "
                   f"{', '.join(generator.passed_over)}.")
    out += [
        "static Rental sOuRentals[] = {",
    ]
    for r in records:
        stat_exp = ", ".join(f"0x{v:04X}" for v in r["stat_exp"])
        moves = ", ".join(str(m) for m in r["moves"])
        out.append(f"    /* {c_comment(generator.comment(r))} */")
        out.append(f"    {{ {LEVEL}, {r['species']}, 0x{r['item']:02X}, 0, {{ {moves} }}, 0, {r['happiness']}, "
                   f"{{ {stat_exp} }}, 0x{r['dvs']:04X}, {{ 0, 0 }} }},")
    out += ["};", f"#define NUM_OU_RENTALS {len(records)}"]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fetch", action="store_true", help="download the pinned source data first")
    args = parser.parse_args()

    if args.fetch:
        legal.fetch(args.cache)
        fetch(args.cache)
    missing = [SOURCES[k][3] for k in SOURCES if not cache_path(args.cache, k).exists()]
    missing += [legal.SOURCES[k][3] for k in legal.SOURCES if not legal.cache_path(args.cache, k).exists()]
    if missing:
        print(f"error: missing {', '.join(missing)} in {args.cache}; run with --fetch", file=sys.stderr)
        return 1
    if not BASE_ROM.exists():
        print(f"error: no {BASE_ROM}; run tools/mod/check_rom.py", file=sys.stderr)
        return 1

    generator = Generator(args.cache, BASE_ROM.read_bytes())
    records = generator.records()
    args.out.write_text(render(generator, records), encoding="ascii", newline="\n")
    for note in generator.notes:
        print(note)
    print(f"wrote {args.out}: {len(records)} records, {len(records) * 0x18} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
