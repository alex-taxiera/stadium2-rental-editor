#!/usr/bin/env python3
"""Write the notes for a release of the patch, from mod/CHANGELOG.md.

The notes are that version's entry in the changelog, followed by how to apply the patch
and the checksums of the ROM it expects, the ROM it produces and the patch itself.
GitHub shows a line break in a release's notes as one, unlike in a file, so the entry's
wrapped paragraphs are joined into single lines.

    tools/mod/release_notes.py             # the newest entry
    tools/mod/release_notes.py v1.2.0      # that release; exit 1 if it has no entry

The release workflow (.github/workflows/mod-release.yml) runs this for the tag being
released, so a tag without a changelog entry gets no draft. The checksums are the ones in
mod/checksums.txt; the patch itself is not needed. Standard library only.
"""

import argparse
import re
import sys
from pathlib import Path

import checksums

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = REPO_ROOT / "mod" / "CHANGELOG.md"

# "## v1.2.0", optionally followed by a date or a title.
HEADING = re.compile(r"^## (v\d\S*)(?:\s.*)?$")
# A line that starts something new rather than continuing the paragraph above it.
BLOCK_START = re.compile(r"^\s*([-*+] |\d+[.)] |#|\||>|```|~~~)")


class NotesError(ValueError):
    pass


def read_changelog(text: str) -> list:
    """[(version, body)] in the order the file has them, newest first by convention."""
    entries = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            entries.append((match.group(1), []))
        elif entries:
            entries[-1][1].append(line)
    return [(version, "\n".join(body).strip()) for version, body in entries]


def entry(entries: list, version: str = None) -> tuple:
    if not entries:
        raise NotesError("the changelog has no entries")
    if version is None:
        return entries[0]
    for found, body in entries:
        if found == version:
            if not body:
                raise NotesError(f"the changelog entry for {version} is empty")
            return found, body
    raise NotesError(f"the changelog has no entry for {version}; add a '## {version}' section")


def unwrap(text: str) -> str:
    """Joins the lines of each wrapped paragraph and list item. Code blocks are kept."""
    out = []
    in_code = False
    for line in text.splitlines():
        fence = line.lstrip().startswith(("```", "~~~"))
        continues = (out and out[-1].strip() and line.strip() and not in_code and not fence
                     and not BLOCK_START.match(line) and not out[-1].lstrip().startswith(("#", "|", "```", "~~~")))
        if continues:
            out[-1] += " " + line.strip()
        else:
            out.append(line)
        if fence:
            in_code = not in_code
    return "\n".join(out)


def applying(guide: str) -> str:
    """How to use the patch, with the checksums recorded for this checkout's build."""
    record = checksums.read_record()
    mod_rom, patch = checksums.BUILT
    patch_name = Path(patch).name
    return "\n".join([
        "## Applying the patch",
        "",
        "You need your own Pokémon Stadium 2 (USA) ROM; the patch holds only the changes, not the "
        f"game. Apply `{patch_name}` to a `.z64` ROM with any BPS patcher (Floating IPS, Rom "
        f"Patcher JS). {guide} covers the controls, the known limits and a checklist for real "
        "hardware.",
        "",
        "| | SHA-1 |",
        "|---|---|",
        f"| Original ROM (`NP3E`, revision 0) | `{record[checksums.BASE_ROM]}` |",
        f"| Patched ROM | `{record[mod_rom]}` |",
        f"| `{patch_name}` | `{record[patch]}` |",
    ])


def notes(version: str = None, guide_url: str = None, changelog: Path = CHANGELOG) -> str:
    _, body = entry(read_changelog(changelog.read_text(encoding="utf-8")), version)
    guide = f"The [user guide]({guide_url})" if guide_url else "The user guide (`mod/README.md`)"
    return f"{unwrap(body)}\n\n{applying(guide)}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", nargs="?", help="the release's tag (default: the newest entry)")
    parser.add_argument("--guide-url", help="link to mod/README.md as released")
    args = parser.parse_args()
    try:
        text = notes(args.version, args.guide_url)
    except (NotesError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
