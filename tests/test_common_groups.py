import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from common_groups import GROUPS, female_group, male_group


class CommonGroupsTest(unittest.TestCase):
    def test_known_male_classes(self):
        self.assertEqual(GROUPS[male_group({"class": "Kenyon_Cell"})], "learning_memory")
        self.assertEqual(GROUPS[male_group({"superclass": "vnc_motor"})], "motor_efferent")
        self.assertEqual(GROUPS[male_group({"class": "mechanosensory"})], "mechanosensory")

    def test_known_female_groups(self):
        self.assertEqual(GROUPS[female_group("MB_KC", "central")], "learning_memory")
        self.assertEqual(GROUPS[female_group("VIS_R1R6", "sensory")], "visual_sensory")
        self.assertEqual(GROUPS[female_group("MN_HEAD", "motor")], "motor_efferent")


if __name__ == "__main__":
    unittest.main()
