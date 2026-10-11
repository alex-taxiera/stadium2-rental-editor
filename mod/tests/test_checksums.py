"""The built mod against mod/checksums.txt. Run: python3 -m unittest discover mod/tests"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mod"))

import check_rom  # noqa: E402
import checksums  # noqa: E402

BUILT = [REPO_ROOT / name for name in checksums.BUILT]


class RecordTest(unittest.TestCase):
    def test_record_lists_the_rom_and_both_built_files(self):
        record = checksums.read_record()
        self.assertEqual(list(record), [checksums.BASE_ROM] + checksums.BUILT)
        for digest in record.values():
            self.assertRegex(digest, r"^[0-9a-f]{40}$")

    def test_base_rom_is_the_one_the_mod_is_built_from(self):
        self.assertEqual(checksums.read_record()[checksums.BASE_ROM], check_rom.US_SHA1)

    def test_record_round_trips(self):
        record = checksums.read_record()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checksums.txt"
            checksums.write_record(record, path)
            self.assertEqual(checksums.read_record(path), record)
            self.assertEqual(path.read_text(encoding="ascii"), checksums.RECORD.read_text(encoding="ascii"))

    def test_compare_reports_changed_and_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "same").write_bytes(b"abc")
            (root / "changed").write_bytes(b"abd")
            abc = "a9993e364706816aba3e25717850c26c9cd0d89d"   # SHA-1 of "abc"
            result = checksums.compare({"same": abc, "changed": abc, "missing": abc}, root)
            self.assertEqual(result["same"], (abc, abc))
            self.assertEqual(result["changed"][0], abc)
            self.assertNotEqual(result["changed"][1], abc)
            self.assertEqual(result["missing"], (abc, None))


@unittest.skipUnless(all(path.exists() for path in BUILT), "the mod is not built; run tools/mod/wsl_build.sh mod")
class BuildTest(unittest.TestCase):
    def test_build_matches_the_record(self):
        record = checksums.read_record()
        for name in checksums.BUILT:
            self.assertEqual(checksums.sha1(REPO_ROOT / name), record[name],
                             f"{name} differs from mod/checksums.txt; if the mod changed on purpose, "
                             "run tools/mod/checksums.py update")

    @unittest.skipUnless((REPO_ROOT / checksums.BASE_ROM).exists(), "no base ROM")
    def test_base_rom_matches_the_record(self):
        self.assertEqual(checksums.sha1(REPO_ROOT / checksums.BASE_ROM),
                         checksums.read_record()[checksums.BASE_ROM])


if __name__ == "__main__":
    unittest.main()
