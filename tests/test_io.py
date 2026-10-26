import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from artifactlens.io import write_text


class WriteTextTests(unittest.TestCase):
    def test_creates_nested_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "reports", "2026", "q3.md")
            write_text(target, "body\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "body\n")

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "out.md")
            target.write_text("old", encoding="utf-8")
            write_text(target, "new")
            self.assertEqual(target.read_text(encoding="utf-8"), "new")


if __name__ == "__main__":
    unittest.main()
