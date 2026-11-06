import unittest
from unittest.mock import patch

from scripts.import_hf import import_aya, stable_id


class AutoImportTests(unittest.TestCase):
    def test_aya_adapter_normalizes_language_and_preserves_revision(self):
        rows = [
            {"inputs": "ما حالة الطلب؟", "targets": "سأتحقق من حالة الطلب أولًا.", "language_code": "arb", "user_id": "private"},
            {"inputs": "", "targets": "ignored", "language_code": "eng"},
        ]
        with patch("scripts.import_hf.load_rows", return_value=rows):
            groups = import_aya(
                "CohereLabs/aya_dataset", "abc123", "train", "Apache-2.0",
                "https://www.apache.org/licenses/LICENSE-2.0",
                "https://huggingface.co/datasets/CohereLabs/aya_dataset", 10,
            )
        self.assertEqual(list(groups), ["ar"])
        record = groups["ar"][0]
        self.assertEqual(record["source_revision"], "abc123")
        self.assertEqual(record["lang_code"], "ar")
        self.assertNotIn("user_id", record)
        self.assertEqual(record["human_review_status"], "reviewed")

    def test_stable_id_changes_when_revision_changes(self):
        row = {"inputs": "hello", "targets": "world"}
        self.assertNotEqual(stable_id("source", "rev-a", row, "en"), stable_id("source", "rev-b", row, "en"))


if __name__ == "__main__":
    unittest.main()
