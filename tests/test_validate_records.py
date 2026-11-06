import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_records import validate_file, validate_record


VALID = {
    "id": "source-1",
    "text": "A sufficiently informative multilingual agent record.",
    "lang_code": "en",
    "source": "synthetic-test",
    "source_url": "https://example.org/items/1",
    "license": "CC0-1.0",
    "quality_score": 0.8,
    "human_review_status": "unreviewed",
    "content_type": "sft",
    "provenance": {"retrieved_at": "2026-01-01T00:00:00Z"},
}


class ValidateRecordsTests(unittest.TestCase):
    def test_valid_record_passes(self):
        self.assertEqual(validate_record(VALID), [])

    def test_rejects_missing_provenance_and_out_of_range_score(self):
        record = dict(VALID, quality_score=1.2, provenance={})
        errors = validate_record(record)
        self.assertTrue(any("quality_score" in error for error in errors))
        self.assertTrue(any("retrieved_at" in error for error in errors))

    def test_rejects_noncanonical_language_and_file_mismatch(self):
        errors = validate_record(dict(VALID, lang_code="eng"), expected_language="fr")
        self.assertTrue(any("canonical" in error for error in errors))
        self.assertTrue(any("disagrees" in error for error in errors))

    def test_file_reports_invalid_json_and_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_text(json.dumps(VALID) + "\nnot-json\n", encoding="utf-8")
            errors = validate_file(path)
            self.assertEqual(len(errors), 1)
            self.assertIn(":2:", errors[0])


if __name__ == "__main__":
    unittest.main()
