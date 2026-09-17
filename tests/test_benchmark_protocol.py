import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from benchmark.graders import grade, materialize
from benchmark.lock_manifest import build_manifest, canonical
from benchmark.runner import quota_limited
from benchmark.tasks.definitions import TASKS


class BenchmarkProtocolTest(unittest.TestCase):
    def test_30_balanced_tasks_and_no_condition_leakage(self):
        self.assertEqual(len(TASKS), 30)
        self.assertEqual(set(Counter(task["category"] for task in TASKS).values()), {5})
        for task in TASKS:
            prompt = task["prompt"].lower()
            self.assertNotIn("connectome", prompt)
            self.assertNotIn("identity", prompt)
            self.assertNotIn("condition", prompt)

    def test_manifest_matches_provider_and_tools_across_conditions(self):
        manifest = build_manifest()
        self.assertEqual(set(manifest["conditions"]), {"identity", "real"})
        self.assertEqual(manifest["seeds"], [101, 202, 303])
        self.assertTrue(manifest["locked"])
        self.assertGreater(len(canonical(manifest)), 1000)

    def test_same_task_materializes_to_same_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a"
            second = Path(directory) / "b"
            self.assertEqual(materialize(TASKS[0], first), materialize(TASKS[0], second))

    def test_exact_grader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "task"
            materialize(TASKS[5], root)
            expected = TASKS[5]["grader"]["expected"]
            for name, content in expected.items():
                (root / name).write_text(content, encoding="utf-8", newline="")
            self.assertTrue(grade(TASKS[5], root)["success"])

    def test_quota_errors_are_detected_without_matching_normal_output(self):
        self.assertTrue(quota_limited("Resource exhausted: usage limit reached"))
        self.assertTrue(quota_limited("HTTP 429: too many requests"))
        self.assertFalse(quota_limited("Task completed successfully"))


if __name__ == "__main__":
    unittest.main()
