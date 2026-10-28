import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curveprotocol.io import InputError, load_book_document, load_records, parse_reserves, write_json, write_text


class WriterTests(unittest.TestCase):
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

    def test_json_writer_sorts_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "deep", "out.json")
            write_json(target, {"b": 1, "a": 2})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 2, "b": 1})


class ReaderTests(unittest.TestCase):
    def test_reads_jsonl_and_skips_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "j.jsonl")
            path.write_text('# note\n{"id": "a"}\n\n{"id": "b"}\n', encoding="utf-8")
            self.assertEqual([r["id"] for r in load_records(path)], ["a", "b"])

    def test_reads_json_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "j.json")
            path.write_text('[{"id": "a"}]', encoding="utf-8")
            self.assertEqual(len(load_records(path)), 1)

    def test_broken_line_reports_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "j.jsonl")
            path.write_text("{}\n{oops\n", encoding="utf-8")
            with self.assertRaises(InputError) as ctx:
                load_records(path)
            self.assertIn(":2:", str(ctx.exception))

    def test_missing_file(self):
        with self.assertRaises(InputError):
            load_records(Path("nope.jsonl"))

    def test_document_needs_an_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "j.json")
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(InputError):
                load_book_document(path)

    def test_reserve_without_id_rejected(self):
        with self.assertRaises(InputError):
            parse_reserves([{"band": "core"}])


if __name__ == "__main__":
    unittest.main()
