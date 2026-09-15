import json
import unittest
from pathlib import Path


class SelfModelProbeTest(unittest.TestCase):
    def test_probe_conditions_are_blinded_and_non_reinforcing(self):
        path = Path(__file__).parents[1] / "web" / "data" / "self_model_probes.json"
        probes = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(probes), 6)
        self.assertEqual(len({item["probe_condition"] for item in probes}), 6)
        for item in probes:
            self.assertTrue(item["blinded"])
            self.assertEqual(item["domain"], "self-model")
            self.assertNotIn("threat", item["options"][item["answer"]].lower())
            self.assertIn(item["answer"], range(4))


if __name__ == "__main__":
    unittest.main()
