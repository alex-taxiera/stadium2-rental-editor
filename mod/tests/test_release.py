"""A release's notes, from mod/CHANGELOG.md. Run: python3 -m unittest discover mod/tests

Nothing here needs the ROM or a build, so all of it runs in the release workflow.
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import checksums  # noqa: E402
import release_notes  # noqa: E402


class ChangelogTest(unittest.TestCase):
    TEXT = ("# Changelog\n\nIntro.\n\n"
            "## v1.1.0 - 2026-11-02\n\nSecond.\n\n- a\n- b\n\n"
            "## v1.0.0\nFirst.\n\n"
            "## v0.9.0-rc1\n")

    def test_entries_are_split_at_version_headings(self):
        self.assertEqual(release_notes.read_changelog(self.TEXT),
                         [("v1.1.0", "Second.\n\n- a\n- b"), ("v1.0.0", "First."), ("v0.9.0-rc1", "")])

    def test_entry_by_version_and_newest_by_default(self):
        entries = release_notes.read_changelog(self.TEXT)
        self.assertEqual(release_notes.entry(entries), ("v1.1.0", "Second.\n\n- a\n- b"))
        self.assertEqual(release_notes.entry(entries, "v1.0.0"), ("v1.0.0", "First."))

    def test_missing_and_empty_entries_are_errors(self):
        entries = release_notes.read_changelog(self.TEXT)
        for version in ("v2.0.0", "v1.0", "v0.9.0-rc1"):
            with self.assertRaises(release_notes.NotesError, msg=version):
                release_notes.entry(entries, version)
        with self.assertRaises(release_notes.NotesError):
            release_notes.entry([])

    def test_the_real_changelog_has_no_repeated_or_empty_entries(self):
        entries = release_notes.read_changelog(release_notes.CHANGELOG.read_text(encoding="utf-8"))
        self.assertTrue(entries)
        versions = [version for version, _ in entries]
        self.assertEqual(len(versions), len(set(versions)))
        for version, body in entries:
            self.assertTrue(body, version)


class UnwrapTest(unittest.TestCase):
    def test_wrapped_paragraphs_and_list_items_become_single_lines(self):
        text = ("A paragraph\nover two lines.\n\n"
                "- one item\n  continued\n- another\n1. numbered\n   continued\n\n"
                "### Heading\nText after it\nwrapped.\n\n"
                "| a | b |\n|---|---|\n| 1 | 2 |\nafter the table")
        self.assertEqual(release_notes.unwrap(text),
                         "A paragraph over two lines.\n\n"
                         "- one item continued\n- another\n1. numbered continued\n\n"
                         "### Heading\nText after it wrapped.\n\n"
                         "| a | b |\n|---|---|\n| 1 | 2 |\nafter the table")

    def test_code_blocks_are_left_alone(self):
        text = "Run:\n\n```\none\n  two\n```\nthen\nthis."
        self.assertEqual(release_notes.unwrap(text), "Run:\n\n```\none\n  two\n```\nthen this.")


class NotesTest(unittest.TestCase):
    def test_notes_are_the_entry_then_the_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(ChangelogTest.TEXT, encoding="utf-8")
            notes = release_notes.notes("v1.0.0", "https://example.org/guide", changelog)
        self.assertTrue(notes.startswith("First.\n\n## Applying the patch\n"))
        self.assertNotIn("Second.", notes)
        self.assertIn("[user guide](https://example.org/guide)", notes)
        record = checksums.read_record()
        for name in [checksums.BASE_ROM] + checksums.BUILT:
            self.assertIn(record[name], notes)

    def test_notes_for_the_newest_real_entry(self):
        notes = release_notes.notes()
        self.assertIn("## Applying the patch", notes)
        self.assertIn(Path(checksums.BUILT[1]).name, notes)


if __name__ == "__main__":
    unittest.main()
