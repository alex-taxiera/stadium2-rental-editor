#!/usr/bin/env python3
"""Generate the move-legality table for the rental editor.

A move is legal for a species if the species, or any earlier stage in its evolution
line, can learn it in Generation 1 or 2 by level-up (L), TM/HM (M), move tutor (T)
or as an egg move (E). Event-only moves (S) are excluded unless --include-events.

Two sources are combined:
  * Pokemon Showdown's Gen 2 learnsets (MIT) for every learn method, and
  * the Gold and Crystal level-up tables from the pret disassemblies, which are the
    games' own data and fill gaps in Showdown's (e.g. Porygon's Conversion 2).

Smeargle may know anything Sketch can copy in Gen 2: every move except Struggle
(rejected by the game's Sketch routine) and Explosion/Selfdestruct (the target
faints, so there is nothing left to copy in a single battle).

Legality is per move. Combinations that cannot coexist on one Pokemon (for example
two egg moves needing different fathers) are not detected, and neither are level
requirements, which the stock rentals ignore as well.

Inputs are pinned by commit and cached in mod/data/cache; pass --fetch to download
them. Standard library only.

    tools/mod/gen_legal_moves.py --fetch     # download pinned data, then generate
    tools/mod/gen_legal_moves.py             # regenerate from the cache
    tools/mod/gen_legal_moves.py --report    # also list where the two sources disagree
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path

# (GitHub repo, commit, path in repo) -> path in the cache directory
SOURCES = {
    "learnsets": ("smogon/pokemon-showdown", "942cda71d14bf0618bd57991708a2e2734b6daba",
                  "data/mods/gen2/learnsets.ts", "showdown/data_mods_gen2_learnsets.ts"),
    "moves": ("smogon/pokemon-showdown", "942cda71d14bf0618bd57991708a2e2734b6daba",
              "data/moves.ts", "showdown/data_moves.ts"),
    "pokedex": ("smogon/pokemon-showdown", "942cda71d14bf0618bd57991708a2e2734b6daba",
                "data/pokedex.ts", "showdown/data_pokedex.ts"),
    "showdown_license": ("smogon/pokemon-showdown", "942cda71d14bf0618bd57991708a2e2734b6daba",
                         "LICENSE", "showdown/LICENSE"),
    "crystal_levelup": ("pret/pokecrystal", "3bc8daa4173e96a7f4011dad3922eb6fa5dad5c6",
                        "data/pokemon/evos_attacks.asm", "pret/crystal_evos_attacks.asm"),
    "gold_levelup": ("pret/pokegold", "ef0201d8daf47e8b3ea1518eacf890f37d4cd5e8",
                     "data/pokemon/evos_attacks.asm", "pret/gold_evos_attacks.asm"),
    "crystal_egg": ("pret/pokecrystal", "3bc8daa4173e96a7f4011dad3922eb6fa5dad5c6",
                    "data/pokemon/egg_moves.asm", "pret/crystal_egg_moves.asm"),
    "gold_egg": ("pret/pokegold", "ef0201d8daf47e8b3ea1518eacf890f37d4cd5e8",
                 "data/pokemon/egg_moves.asm", "pret/gold_egg_moves.asm"),
}
LEVELUP_SOURCES = ("crystal_levelup", "gold_levelup")
EGG_SOURCES = ("crystal_egg", "gold_egg")

# Fetched alongside the sources but only used by mod/tests: the stock rental tables.
TEST_SOURCES = {
    name: ("pret/pokestadium", "6995f32445e344c03f9b0c774eabcd157559f867",
           f"oldnotes/stadiumgs/rentals/{name}.json", f"rentals/{name}.json")
    for name in ("littlecup", "pokecup", "primecup1", "primecup2")
}

NUM_SPECIES = 251
NUM_MOVES = 251
ROW_BYTES = (NUM_MOVES + 8) // 8  # bit index is the move id, so ids 0..251 need 32 bytes

LEGAL_SOURCE_TYPES = "LMTE"
EVENT_SOURCE_TYPE = "S"
SMEARGLE = "smeargle"
SKETCH_EXCLUDED = ("struggle", "explosion", "selfdestruct")

# pret constant names (after to_id) that differ from Showdown's move ids.
PRET_MOVE_ALIASES = {
    "psychicm": "psychic",
    "hijumpkick": "highjumpkick",
    "faintattack": "feintattack",
    "vicegrip": "visegrip",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = REPO_ROOT / "mod" / "data" / "cache"
DEFAULT_OUT = REPO_ROOT / "mod" / "data" / "legal_moves.inc.c"

ENTRY_START = re.compile(r"^\t(\w+): \{$")
ENTRY_END = re.compile(r"^\t\},?$")
FIELD_NUM = re.compile(r"^\t\tnum: (-?\d+),$")
FIELD_STR = re.compile(r'^\t\t(name|prevo|baseSpecies|forme): "(.*)",$')
LEARNSET_MOVE = re.compile(r"^\t\t\t(\w+): \[(.*)\],$")
SOURCE = re.compile(r'"(\d)([A-Z])\d*"')
PRET_LABEL = re.compile(r"^(\w+?)(EvosAttacks|EggMoves):")
PRET_LEVEL_MOVE = re.compile(r"^\tdb (\d+), (\w+)")
PRET_EGG_MOVE = re.compile(r"^\tdb ([A-Z]\w*)")


def to_id(name: str) -> str:
    """Showdown's toID: lower-case ASCII alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def cache_path(cache: Path, key: str) -> Path:
    return cache / SOURCES[key][3]


def fetch(cache: Path) -> None:
    for repo, commit, remote, local in list(SOURCES.values()) + list(TEST_SOURCES.values()):
        url = f"https://raw.githubusercontent.com/{repo}/{commit}/{remote}"
        print(f"fetching {url}")
        dest = cache / local
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as r:
            dest.write_bytes(r.read())


def iter_entries(path: Path):
    """Yield (id, lines) for each top-level `id: { ... },` block of a Showdown data file."""
    current, lines = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if current is None:
            m = ENTRY_START.match(line)
            if m:
                current, lines = m.group(1), []
        elif ENTRY_END.match(line):
            yield current, lines
            current = None
        else:
            lines.append(line)


def parse_moves(path: Path) -> dict:
    """Move id -> number, for Gen 1-2 moves."""
    moves = {}
    for move_id, lines in iter_entries(path):
        for line in lines:
            m = FIELD_NUM.match(line)
            if m:
                num = int(m.group(1))
                if 1 <= num <= NUM_MOVES:
                    moves[move_id] = num
                break
    return moves


def alphabetical_moves(moves: dict) -> list:
    """Move numbers ordered by name as the game spells it.

    Several ids share a number (the typed Hidden Powers); the plain one sorts first
    and is the one kept.
    """
    in_game = {new: old for old, new in PRET_MOVE_ALIASES.items() if old != "psychicm"}
    order = []
    for move_id in sorted(moves, key=lambda i: in_game.get(i, i)):
        if moves[move_id] not in order:
            order.append(moves[move_id])
    return order


def parse_pokedex(path: Path) -> dict:
    """Species id -> {num, name, prevo} for base forms of the first 251 species."""
    species = {}
    for species_id, lines in iter_entries(path):
        fields = {}
        for line in lines:
            m = FIELD_NUM.match(line)
            if m:
                fields.setdefault("num", int(m.group(1)))
                continue
            m = FIELD_STR.match(line)
            if m:
                fields.setdefault(m.group(1), m.group(2))
        num = fields.get("num", 0)
        if not 1 <= num <= NUM_SPECIES or "baseSpecies" in fields or "forme" in fields:
            continue
        species[species_id] = {
            "num": num,
            "name": fields.get("name", species_id),
            "prevo": to_id(fields["prevo"]) if "prevo" in fields else None,
        }
    return species


def parse_learnsets(path: Path) -> dict:
    """Species id -> {move id -> set of (generation, source type)}."""
    learnsets = {}
    for species_id, lines in iter_entries(path):
        moves = {}
        for line in lines:
            m = LEARNSET_MOVE.match(line)
            if m:
                moves[m.group(1)] = {(int(g), t) for g, t in SOURCE.findall(m.group(2))}
        learnsets[species_id] = moves
    return learnsets


def pret_move_id(constant: str) -> str:
    move_id = to_id(constant)
    return PRET_MOVE_ALIASES.get(move_id, move_id)


def parse_pret_levelup(path: Path) -> dict:
    """Species id -> set of move ids, from a pret Gen 2 evos_attacks.asm."""
    result, species, in_moves = {}, None, False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PRET_LABEL.match(line)
        if m:
            species, in_moves = to_id(m.group(1)), False
            result[species] = set()
            continue
        if species is None:
            continue
        if line.startswith("\tdb 0"):
            # First terminator ends the evolution list, the second ends the move list.
            species = species if not in_moves else None
            in_moves = True
            continue
        m = PRET_LEVEL_MOVE.match(line)
        if in_moves and m:
            result[species].add(pret_move_id(m.group(2)))
    return result


def parse_pret_egg(path: Path) -> dict:
    """Species id -> set of move ids, from a pret Gen 2 egg_moves.asm."""
    result, species = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PRET_LABEL.match(line)
        if m:
            species = to_id(m.group(1))
            result[species] = set()
        elif species is not None:
            m = PRET_EGG_MOVE.match(line)
            if m:
                result[species].add(pret_move_id(m.group(1)))
            elif line.startswith("\tdb -1"):
                species = None
    return result


def evolution_line(species_id: str, pokedex: dict) -> list:
    """The species followed by its earlier stages. Later-generation babies are not in pokedex."""
    line = []
    while species_id in pokedex and species_id not in line:
        line.append(species_id)
        species_id = pokedex[species_id]["prevo"]
    return line


def own_moves(species_id: str, learnsets: dict, levelup: dict, allowed: str) -> set:
    """Move ids the species itself learns, before inheriting from earlier stages."""
    moves = {move for move, sources in learnsets.get(species_id, {}).items()
             if any(g <= 2 and t in allowed for g, t in sources)}
    return moves | levelup.get(species_id, set())


def build_table(pokedex: dict, learnsets: dict, levelup: dict, moves: dict,
                include_events: bool = False) -> dict:
    """Species number -> set of legal move numbers."""
    allowed = LEGAL_SOURCE_TYPES + (EVENT_SOURCE_TYPE if include_events else "")
    table = {}
    for species_id, info in pokedex.items():
        legal = set()
        for stage in evolution_line(species_id, pokedex):
            legal |= {moves[m] for m in own_moves(stage, learnsets, levelup, allowed)}
        if species_id == SMEARGLE:
            legal = set(range(1, NUM_MOVES + 1)) - {moves[m] for m in SKETCH_EXCLUDED}
        table[info["num"]] = legal
    return table


class Data:
    """Everything parsed from the cache."""

    def __init__(self, cache: Path):
        self.moves = parse_moves(cache_path(cache, "moves"))
        self.pokedex = parse_pokedex(cache_path(cache, "pokedex"))
        self.learnsets = parse_learnsets(cache_path(cache, "learnsets"))
        self.levelup = {}
        for key in LEVELUP_SOURCES:
            for species, learned in parse_pret_levelup(cache_path(cache, key)).items():
                self.levelup.setdefault(species, set()).update(learned)
        self.egg = {key: parse_pret_egg(cache_path(cache, key)) for key in EGG_SOURCES}

    def table(self, include_events: bool = False) -> dict:
        return build_table(self.pokedex, self.learnsets, self.levelup, self.moves, include_events)

    def validate(self) -> list:
        errors = []
        if len(self.pokedex) != NUM_SPECIES:
            errors.append(f"expected {NUM_SPECIES} species, parsed {len(self.pokedex)}")
        if len(set(self.moves.values())) != NUM_MOVES:
            errors.append(f"expected {NUM_MOVES} moves, parsed {len(set(self.moves.values()))}")
        if set(self.levelup) != set(self.pokedex):
            errors.append(f"pret level-up species differ: {sorted(set(self.levelup) ^ set(self.pokedex))}")
        unknown = {m for learned in self.levelup.values() for m in learned} - set(self.moves)
        for eggs in self.egg.values():
            unknown |= {m for learned in eggs.values() for m in learned} - set(self.moves)
        if unknown:
            errors.append(f"unknown pret move names: {sorted(unknown)}")
        return errors

    def report(self) -> list:
        """Where Showdown's Gen 2 data and the game data disagree."""
        lines = []
        for species in sorted(self.pokedex, key=lambda s: self.pokedex[s]["num"]):
            showdown = {m for m, src in self.learnsets.get(species, {}).items() if (2, "L") in src}
            game = self.levelup.get(species, set())
            for move in sorted(game - showdown):
                lines.append(f"level-up in game data, missing from Showdown: {species} {move}")
            for move in sorted(showdown - game):
                lines.append(f"level-up in Showdown, missing from game data: {species} {move}")
            showdown_egg = {m for m, src in self.learnsets.get(species, {}).items() if (2, "E") in src}
            game_egg = set().union(*(eggs.get(species, set()) for eggs in self.egg.values()))
            for move in sorted(game_egg - showdown_egg):
                lines.append(f"egg move in game data, not an egg move in Showdown: {species} {move}")
            for move in sorted(showdown_egg - game_egg):
                lines.append(f"egg move in Showdown, missing from game data: {species} {move}")
        return lines


def pack_row(legal: set) -> bytes:
    row = bytearray(ROW_BYTES)
    for move in legal:
        row[move >> 3] |= 1 << (move & 7)
    return bytes(row)


def render(table: dict, pokedex: dict, move_order: list, include_events: bool) -> str:
    names = {info["num"]: info["name"].encode("ascii", "replace").decode() for info in pokedex.values()}
    out = [
        "// Generated by tools/mod/gen_legal_moves.py. Do not edit by hand.",
        f"// Sources: Pokemon Showdown gen2 learnsets @ {SOURCES['learnsets'][1][:12]} (MIT);",
        f"// level-up tables from pret/pokecrystal @ {SOURCES['crystal_levelup'][1][:12]}"
        f" and pret/pokegold @ {SOURCES['gold_levelup'][1][:12]}.",
        "// Row = national dex number, bit = move id: (row[move >> 3] >> (move & 7)) & 1.",
        f"// Methods: level-up, TM/HM, tutor, egg{', event' if include_events else ''}; "
        "Gen 1 and 2; earlier evolution stages included.",
        f"static const u8 sLegalMoves[{NUM_SPECIES + 1}][{ROW_BYTES}] = {{",
        "    { 0 },",
    ]
    for num in range(1, NUM_SPECIES + 1):
        cells = ", ".join(f"0x{b:02X}" for b in pack_row(table[num]))
        out.append(f"    {{ {cells} }}, // {num:3d} {names[num]} ({len(table[num])})")
    out += ["};", "", "// Every move id, in alphabetical order of its name.",
            f"static const u8 sMoveOrder[{NUM_MOVES}] = {{"]
    for start in range(0, NUM_MOVES, 16):
        out.append("    " + ", ".join(f"{m:3d}" for m in move_order[start:start + 16]) + ",")
    out.append("};")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fetch", action="store_true", help="download the pinned source data first")
    parser.add_argument("--include-events", action="store_true", help="also allow event-only moves")
    parser.add_argument("--report", action="store_true", help="list disagreements between the sources")
    args = parser.parse_args()

    if args.fetch:
        fetch(args.cache)
    missing = [SOURCES[k][3] for k in SOURCES if not cache_path(args.cache, k).exists()]
    if missing:
        print(f"error: missing {', '.join(missing)} in {args.cache}; run with --fetch", file=sys.stderr)
        return 1

    data = Data(args.cache)
    errors = data.validate()
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 1

    if args.report:
        lines = data.report()
        print("\n".join(lines) if lines else "sources agree")
        print(f"{len(lines)} disagreement(s)")

    table = data.table(args.include_events)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(table, data.pokedex, alphabetical_moves(data.moves), args.include_events),
                        encoding="ascii", newline="\n")
    sizes = sorted(len(v) for v in table.values())
    print(f"wrote {args.out}")
    print(f"species: {len(table)}  moves: {NUM_MOVES}  table: {(NUM_SPECIES + 1) * ROW_BYTES} bytes")
    print(f"legal moves per species: min {sizes[0]}, median {sizes[len(sizes) // 2]}, max {sizes[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
