import json
import unittest
from pathlib import Path


DATA = Path(__file__).parents[1] / "web" / "data"


class CommonGraphArtifactsTest(unittest.TestCase):
    def load(self, sex):
        return json.loads((DATA / f"{sex}_common_graph.json").read_text(encoding="utf-8"))

    def test_shared_shape_and_normalization(self):
        male, female = self.load("male"), self.load("female")
        self.assertEqual(male["groups"], female["groups"])
        for graph in (male, female):
            self.assertEqual(len(graph["groups"]), 16)
            self.assertEqual(len(graph["weights"]), 16)
            self.assertTrue(all(len(row) == 16 for row in graph["weights"]))
            self.assertTrue(all(sum(abs(x) for x in row) <= 1.000001 for row in graph["weights"]))

    def test_male_release_audit(self):
        graph = self.load("male")
        self.assertEqual(graph["annotation_rows"], 211_577)
        self.assertEqual(graph["publication_neurons"], 166_691)
        self.assertEqual(graph["retained_neurons"], 166_700)
        self.assertEqual(sum(graph["group_neurons"]), 166_700)
        self.assertEqual(graph["source_edge_pairs"], 151_856_684)
        self.assertEqual(graph["kept_signed_edge_pairs"], 24_994_676)
        self.assertEqual(graph["kept_synapses"], 122_129_173)
        self.assertEqual(
            graph["source_sha256"]["connectome-weights-male-cns-v1.0-minconf-0.5.feather"],
            "e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1",
        )

    def test_female_release_audit(self):
        graph = self.load("female")
        self.assertEqual(graph["source_neurons"], 139_255)
        self.assertEqual(graph["source_edges"], 2_698_236)
        self.assertEqual(sum(graph["group_neurons"]), 139_255)


if __name__ == "__main__":
    unittest.main()
