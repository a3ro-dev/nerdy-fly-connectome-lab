import unittest

from benchmark.statistics import aggregate, bootstrap_ci, mcnemar_exact


class StatisticsTest(unittest.TestCase):
    def test_mcnemar_exact(self):
        self.assertEqual(mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(mcnemar_exact(0, 5), 0.0625)

    def test_bootstrap_is_deterministic(self):
        self.assertEqual(bootstrap_ci([1, 2, 3], samples=100), bootstrap_ci([1, 2, 3], samples=100))

    def test_aggregate_pairs_by_task_and_seed(self):
        base = {"category":"x","seed":1,"wall_clock_time":1.0,"infrastructure_failure":None}
        runs = [
            {**base,"task_id":"a","condition":"identity","success":False},
            {**base,"task_id":"a","condition":"real","success":True},
        ]
        result = aggregate(runs)
        self.assertEqual(result["complete_pairs"], 1)
        self.assertEqual(result["paired_success_difference"], 1.0)


if __name__ == "__main__":
    unittest.main()
