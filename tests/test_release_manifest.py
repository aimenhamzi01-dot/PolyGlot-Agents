import json
import tempfile
import unittest
from pathlib import Path

from evaluation.release_manifest import build_manifest


class ReleaseManifestTests(unittest.TestCase):
    def test_manifest_contains_hashes_and_review_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        benchmark = root / "evaluation" / "benchmarks" / "en_tasks.json"
        manifest = build_manifest(benchmark, repository_root=root)
        self.assertEqual(manifest["benchmark_review_status"], "unreviewed")
        self.assertEqual(manifest["hidden_test_status"], "not_provisioned")
        self.assertTrue(any(item["path"] == "evaluation/benchmarks/en_tasks.json" for item in manifest["files"]))
        self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["files"]))

    def test_report_must_reference_exact_benchmark_bytes(self):
        root = Path(__file__).resolve().parents[1]
        benchmark = root / "evaluation" / "benchmarks" / "en_tasks.json"
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            report.write_text(json.dumps({"benchmark_sha256": "0" * 64, "aggregate": {}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                build_manifest(benchmark, report=report, repository_root=root)

    def test_external_report_is_marked_without_breaking_manifest(self):
        root = Path(__file__).resolve().parents[1]
        benchmark = root / "evaluation" / "benchmarks" / "en_tasks.json"
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            import hashlib
            report.write_text(json.dumps({"benchmark_sha256": hashlib.sha256(benchmark.read_bytes()).hexdigest(), "aggregate": {}}), encoding="utf-8")
            manifest = build_manifest(benchmark, report=report, repository_root=root)
            self.assertTrue(any(item["path"] == "external:report.json" for item in manifest["files"]))


if __name__ == "__main__":
    unittest.main()
