import json
import tempfile
import unittest
from pathlib import Path

from scripts.fine_tune import format_record, read_records, split_records


class FakeTokenizer:
    chat_template = "available"

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        assert tokenize is False
        assert add_generation_prompt is False
        return "\n".join(f"<{m['role']}> {m['content']}" for m in messages)


class FineTuneTests(unittest.TestCase):
    def test_format_record_prefers_chat_template(self):
        row = {"text": "fallback", "messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]}
        self.assertEqual(format_record(row, FakeTokenizer()), "<user> hi\n<assistant> hello")

    def test_read_records_keeps_reviewed_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.jsonl"
            rows = [
                {"id": "1", "text": "one", "human_review_status": "reviewed"},
                {"id": "1", "text": "duplicate", "human_review_status": "reviewed"},
                {"id": "2", "text": "two", "human_review_status": "unreviewed"},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            records = read_records([path])
            self.assertEqual([row["id"] for row in records], ["1"])
            self.assertEqual(len(read_records([path], include_unreviewed=True)), 2)

    def test_split_is_reproducible_and_retains_all_records(self):
        rows = [{"id": str(i), "text": str(i)} for i in range(10)]
        train_a, eval_a = split_records(rows, 0.2, 7)
        train_b, eval_b = split_records(rows, 0.2, 7)
        self.assertEqual(train_a, train_b)
        self.assertEqual(eval_a, eval_b)
        self.assertEqual(len(train_a) + len(eval_a), len(rows))


if __name__ == "__main__":
    unittest.main()
