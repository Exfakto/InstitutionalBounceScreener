import unittest

from analysis import BaseScore


class BaseScoreTest(unittest.TestCase):

    def test_base_score_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            BaseScore()

    def test_clamp_bounds_values(self):
        self.assertEqual(BaseScore.clamp(-10), 0.0)
        self.assertEqual(BaseScore.clamp(50), 50.0)
        self.assertEqual(BaseScore.clamp(110), 100.0)


if __name__ == "__main__":
    unittest.main()
