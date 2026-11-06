import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.auto_import import load_sources
from scripts.import_hf import import_aya, stable_id
from scripts.rights_engine import RightsError, validate_record, validate_source


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

    def test_configured_sources_pass_fail_closed_rights_gate(self):
        sources = load_sources(Path("configs/sources.yaml"))
        validate_source("openassistant_oasst1", sources["openassistant_oasst1"])
        validate_source("aya_dataset", sources["aya_dataset"])

    def test_unknown_license_is_rejected(self):
        cfg = {"dataset_card": "https://example.test/card", "license": "unknown", "license_url": "https://example.test/license", "rights_status": "reviewed", "allowed_uses": ["research"], "redistribution": True, "commercial_use": "review_required"}
        with self.assertRaises(RightsError):
            validate_source("untrusted", cfg)

    def test_missing_record_rights_are_rejected(self):
        with self.assertRaises(RightsError):
            validate_record({"id": "x", "text": "hello"})


if __name__ == "__main__":
    unittest.main()
