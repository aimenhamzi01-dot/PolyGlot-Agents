import json
import tempfile
import unittest
from pathlib import Path

from evaluation.coverage_dashboard import collect_rows, render_html, render_markdown


class CoverageDashboardTests(unittest.TestCase):
    def test_rows_distinguish_data_coverage_from_benchmark_status(self):
        coverage = {"languages": {"ar": {"records": 3, "quality_score": {"mean": 0.8}, "human_review_status": {"reviewed": 2}, "review_required": 1}, "xx": {"records": 1}}}
        with tempfile.TemporaryDirectory() as directory:
            benchmark_dir = Path(directory)
            (benchmark_dir / "ar_tasks.json").write_text(json.dumps({"language": "ar", "status": "pending_native_speaker_review"}), encoding="utf-8")
            rows = collect_rows(coverage, benchmark_dir)
        self.assertEqual(rows[0]["benchmark_status"], "pending_native_speaker_review")
        self.assertEqual(rows[1]["benchmark_status"], "no benchmark file")

    def test_renderers_include_disclaimer_and_language_rows(self):
        rows = [{"language": "ar", "records": 3, "quality_mean": 0.8, "reviewed": 2, "review_required": 1, "benchmark_status": "pending_native_speaker_review"}]
        markdown = render_markdown(rows)
        html = render_html(rows)
        self.assertIn("not proof of benchmark support", markdown)
        self.assertIn("pending_native_speaker_review", markdown)
        self.assertIn("<table>", html)
        self.assertIn("ar", html)


if __name__ == "__main__":
    unittest.main()
