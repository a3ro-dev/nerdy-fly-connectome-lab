import json
import tempfile
import unittest
from pathlib import Path

from tools.reasoning_agent import exact_task, retrieve_memories


class ReasoningAgentTest(unittest.TestCase):
    def test_exact_tasks_are_deterministic_and_exact(self):
        self.assertEqual(exact_task(7), exact_task(7))
        prompt, answer = exact_task(8)
        self.assertIn("Return only the integer", prompt)
        self.assertRegex(answer, r"^-?\d+$")

    def test_retrieval_is_scored_and_excludes_current_page(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            rows = [
                {"cycle":1,"source_url":"https://a.test","summary":"quantum field measurement","hypothesis":"measurement changes evidence"},
                {"cycle":2,"source_url":"https://b.test","summary":"poetry and metaphor","hypothesis":"literary form"},
                {"cycle":3,"source_url":"https://current.test","summary":"quantum quantum field","hypothesis":"must be excluded"},
                {"cycle":4,"source_url":"https://meta.test","summary":"quantum field attention score","hypothesis":"connectome cognitive deficit"},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            memories = retrieve_memories(path, "quantum field theory", "https://current.test")
            self.assertEqual([item["url"] for item in memories], ["https://a.test"])


if __name__ == "__main__":
    unittest.main()
