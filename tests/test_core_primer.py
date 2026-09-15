import hashlib
import json
import unittest
from pathlib import Path


class CorePrimerTest(unittest.TestCase):
    def test_seed_is_explicit_and_bounded(self):
        path = Path(__file__).parents[1] / "web" / "data" / "core_primer.json"
        raw = path.read_bytes(); primer = json.loads(raw)
        self.assertEqual(primer["version"], 2)
        self.assertNotIn("identity", primer)
        self.assertGreaterEqual(len(primer["general_constraints"]), 6)
        self.assertIn("science", primer["knowledge_map"])
        self.assertIn("literature", primer["knowledge_map"])
        withheld = " ".join(primer["explicitly_withheld"]).lower()
        self.assertIn("simulated", withheld)
        self.assertIn("resurrection", withheld)
        self.assertEqual(len(hashlib.sha256(raw).hexdigest()), 64)


if __name__ == "__main__":
    unittest.main()
