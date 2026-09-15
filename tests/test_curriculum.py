import json
import unittest
from collections import Counter
from pathlib import Path


class CurriculumTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[1] / "web" / "data" / "curriculum.json"
        cls.lessons = json.loads(path.read_text(encoding="utf-8"))

    def test_balanced_domains(self):
        self.assertEqual(
            Counter(x["domain"] for x in self.lessons),
            {"science": 4, "math": 4, "ai": 4, "physics": 4, "philosophy": 4, "literature": 4},
        )

    def test_exact_grader_contract(self):
        self.assertEqual(len(self.lessons), 24)
        for lesson in self.lessons:
            self.assertEqual(len(lesson["options"]), 4)
            self.assertIn(lesson["answer"], range(4))
            for field in ("title", "question", "lesson", "source"):
                self.assertTrue(lesson[field].strip())


if __name__ == "__main__":
    unittest.main()
