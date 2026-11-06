import json
import tempfile
import unittest
from pathlib import Path

from scripts.rights_lifecycle import build_manifest, quarantine


class RightsLifecycleTests(unittest.TestCase):
    def test_manifest_tracks_source_file_line_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "data"
            root.mkdir()
            path = root / "records.jsonl"
            path.write_text(
                json.dumps({"id": "a", "source": "source-one", "text": "A"}) + "\n"
                + json.dumps({"id": "b", "source": "source-two", "text": "B"}) + "\n",
                encoding="utf-8",
            )
            manifest = build_manifest(root)
            self.assertEqual(manifest["record_count"], 2)
            self.assertEqual(manifest["records"][0]["file"], str(path))
            self.assertEqual(manifest["records"][0]["line"], 1)
            self.assertEqual(len(manifest["records"][0]["record_sha256"]), 64)

    def test_quarantine_is_non_destructive_and_writes_tombstones(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "data"
            root.mkdir()
            path = root / "records.jsonl"
            original = [
                {"id": "a", "source": "source-one", "text": "A"},
                {"id": "b", "source": "source-two", "text": "B"},
            ]
            path.write_text("\n".join(json.dumps(row) for row in original) + "\n", encoding="utf-8")
            output = Path(directory) / "quarantine"
            summary = quarantine(root, output, record_ids={"a"}, sources=set(), reason="deletion_request")
            self.assertEqual(summary, {"kept": 1, "removed": 1, "tombstones": 1})
            self.assertEqual(path.read_text(encoding="utf-8").count("\n"), 2)
            kept = [json.loads(line) for line in (output / "records.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["id"] for row in kept], ["b"])
            tombstone = json.loads((output / "deletion_manifest.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(tombstone["record_id"], "a")
            self.assertEqual(tombstone["reason"], "deletion_request")

    def test_quarantine_requires_a_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "records.jsonl").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "at least one"):
                quarantine(root, root / "out", record_ids=set(), sources=set(), reason="test")


if __name__ == "__main__":
    unittest.main()
