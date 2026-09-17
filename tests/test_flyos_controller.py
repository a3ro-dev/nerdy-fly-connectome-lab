import json
import tempfile
import unittest
from pathlib import Path

from flyos.controller import CAPABILITIES, Condition, Controller
from flyos.memory import MemoryStore


ROOT = Path(__file__).parents[1]
GRAPH = json.loads((ROOT / "web/data/male_common_graph.json").read_text(encoding="utf-8"))


class ControllerTest(unittest.TestCase):
    def test_conditions_are_matched_but_causally_distinct(self):
        controllers = {condition: Controller(GRAPH, condition, seed=7) for condition in Condition}
        signal = controllers[Condition.REAL].observe("debug code and verify tests")
        outputs = {condition: controller.propagate(signal) for condition, controller in controllers.items()}
        self.assertEqual({len(output) for output in outputs.values()}, {16})
        self.assertNotEqual(outputs[Condition.REAL], outputs[Condition.IDENTITY])
        self.assertNotEqual(outputs[Condition.REAL], outputs[Condition.SHUFFLED])
        self.assertNotEqual(outputs[Condition.REAL], outputs[Condition.REWIRED])
        self.assertNotEqual(controllers[Condition.REAL].fingerprint(), controllers[Condition.IDENTITY].fingerprint())

    def test_rewire_preserves_binary_in_and_out_degree(self):
        real = Controller(GRAPH, Condition.REAL, seed=11).matrix
        rewired = Controller(GRAPH, Condition.REWIRED, seed=11).matrix
        degrees = lambda matrix: (
            [sum(value != 0 for value in row) for row in matrix],
            [sum(matrix[i][j] != 0 for i in range(16)) for j in range(16)],
        )
        self.assertEqual(degrees(real), degrees(rewired))

    def test_reward_requires_verified_transition(self):
        controller = Controller(GRAPH, Condition.REAL)
        self.assertLessEqual(controller.update_from_result({"predicted_reward": 0.5}), 0)
        self.assertGreater(controller.update_from_result({"predicted_reward": 0.5, "state_changed": True, "verified": True}), 0)

    def test_capability_scores_are_bounded(self):
        controller = Controller(GRAPH, Condition.REAL)
        controller.propagate(controller.observe("research sources then verify and synthesize"))
        scores = controller.score_capabilities(CAPABILITIES)
        self.assertTrue(all(0 <= score <= 1 for score in scores.values()))
        self.assertGreater(scores["research"], scores["vision"])


class MemoryTest(unittest.TestCase):
    def test_memory_is_explicit_bounded_and_ranked(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.jsonl")
            store.write("task", "verify alpha checksum", 0.9, "test", {"id": 1}, "needed later")
            store.write("episodic", "unrelated beta", 1.0, "test", {}, "trace")
            result = store.retrieve("alpha verification", limit=1, reason="resume")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["retrieval_reason"], "resume")
            self.assertIn("alpha", result[0]["content"])


if __name__ == "__main__":
    unittest.main()
