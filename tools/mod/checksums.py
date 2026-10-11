#!/usr/bin/env python3
"""Check the built mod against the checksums recorded in mod/checksums.txt.

The build is repeatable: the same sources give the same ROM and the same patch, byte for
byte. Recording their checksums turns that into a test. After moving to a newer commit
of the decompilation, or touching the build tools, an unchanged checksum proves the mod
itself did not change. When the mod's own sources change, the checksums change with
them, and `update` records the new ones.

    tools/mod/checksums.py check     # exit 1 if a built file differs from the record
    tools/mod/checksums.py update    # record the files as built

Run it from the checkout, not the WSL build mirror, so `update` writes the file that is
committed. Standard library only.
"""

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = REPO_ROOT / "mod" / "checksums.txt"

# The original ROM is listed with the others so the record says what the patch applies
# to, but `update` never rewrites its line: it is the one input that must not change.
BASE_ROM = "baseroms/us/baserom.z64"
BUILT = ["build/pokestadiumgs-us-mod.z64", "build/stadium2-rental-editor-us.bps"]


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_record(path: Path = RECORD) -> dict:
    """{file: sha1}, in the format `sha1sum` writes."""
    record = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, name = line.split(None, 1)
            record[name.strip()] = digest
    return record


def write_record(record: dict, path: Path = RECORD) -> None:
    lines = ["# SHA-1 of the original ROM and of what tools/mod/wsl_build.sh mod builds from it.",
             "# Checked by tools/mod/checksums.py; see mod/NOTES.md, \"Tests\"."]
    lines += [f"{digest}  {name}" for name, digest in record.items()]
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def compare(record: dict, root: Path = REPO_ROOT) -> dict:
    """{file: (recorded, actual)} for every recorded file; actual is None if missing."""
    return {name: (digest, sha1(root / name) if (root / name).exists() else None)
            for name, digest in record.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["check", "update"])
    parser.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="where the built files are (default: this checkout)")
    args = parser.parse_args()

    record = read_record()
    if args.command == "update":
        for name in BUILT:
            if not (args.root / name).exists():
                print(f"error: {name} is not built", file=sys.stderr)
                return 1
            record[name] = sha1(args.root / name)
        write_record(record)
        print(f"recorded {len(BUILT)} checksums in {RECORD.relative_to(REPO_ROOT)}")
        return 0

    failed = False
    for name, (recorded, actual) in compare(record, args.root).items():
        if actual == recorded:
            print(f"ok       {name}")
        elif actual is None:
            print(f"missing  {name}")
            failed = True
        else:
            print(f"DIFFERS  {name}\n           recorded {recorded}\n           built    {actual}")
            failed = True
    if failed:
        print("The build does not match mod/checksums.txt. If the mod's sources changed on purpose,\n"
              "record the new build with: tools/mod/checksums.py update", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
