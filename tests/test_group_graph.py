import json
import unittest
from pathlib import Path


class GroupGraphTest(unittest.TestCase):
    def test_shape_counts_and_normalization(self):
        p = Path(__file__).parents[1] / "web" / "data" / "group_graph.json"
        g = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual((g["neuron_count"], g["edge_count"]), (139255, 2698236))
        self.assertEqual(len(g["groups"]), 63)
        self.assertTrue(all(len(row) == 63 for row in g["weights"]))
        for row in g["weights"]:
            norm = sum(map(abs, row))
            self.assertTrue(norm == 0 or abs(norm - 1) <= 1e-6)


if __name__ == "__main__":
    unittest.main()
