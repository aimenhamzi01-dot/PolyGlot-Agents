import unittest

from scripts.review_queue import apply_decisions, create_queue


RECORDS = [
    {"id": "a", "lang_code": "ar", "text": "Arabic record"},
    {"id": "b", "lang_code": "en", "text": "English record"},
    {"id": "c", "lang_code": "ar", "text": "Another Arabic record"},
]


class ReviewQueueTests(unittest.TestCase):
    def test_queue_sampling_is_reproducible_and_language_scoped(self):
        first = create_queue(RECORDS, sample_size=2, seed=7, language="ar")
        second = create_queue(RECORDS, sample_size=2, seed=7, language="ar")
        self.assertEqual(first, second)
        self.assertEqual({item["lang_code"] for item in first}, {"ar"})
        self.assertTrue(all(item["status"] == "pending" for item in first))
        self.assertEqual(len({item["review_id"] for item in first}), 2)

    def test_decision_application_records_auditable_review_metadata(self):
        queue = create_queue(RECORDS, sample_size=1, seed=2)
        item = queue[0]
        updated = apply_decisions(
            RECORDS,
            [{
                "review_id": item["review_id"],
                "record_id": item["record_id"],
                "decision": "reviewed",
                "reviewer_ref": "reviewer-team-ar-01",
                "reviewed_at": "2026-11-06T12:00:00Z",
                "rubric_version": "v1",
                "notes": "accepted after language and safety review",
            }],
        )
        row = next(record for record in updated if record["id"] == item["record_id"])
        self.assertEqual(row["human_review_status"], "reviewed")
        self.assertEqual(row["human_review"]["reviewer_ref"], "reviewer-team-ar-01")

    def test_adjudication_does_not_promote_record(self):
        queue = create_queue(RECORDS, sample_size=1, seed=2)
        item = queue[0]
        updated = apply_decisions(RECORDS, [{
            "review_id": item["review_id"],
            "record_id": item["record_id"],
            "decision": "needs_adjudication",
            "reviewer_ref": "reviewer-team-01",
            "reviewed_at": "2026-11-06T12:00:00Z",
        }])
        row = next(record for record in updated if record["id"] == item["record_id"])
        self.assertEqual(row["human_review_status"], "unreviewed")
        self.assertEqual(row["human_review"]["decision"], "needs_adjudication")

    def test_missing_reviewer_reference_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "reviewer_ref"):
            apply_decisions(RECORDS, [{
                "review_id": "r1", "record_id": "a", "decision": "reviewed", "reviewed_at": "today"
            }])


if __name__ == "__main__":
    unittest.main()
