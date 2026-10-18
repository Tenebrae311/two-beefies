import random
import unittest

from src.random_image_to_text import choose_random_row


class ChooseRandomRowTests(unittest.TestCase):
    def test_selects_one_uniform_reservoir_candidate(self):
        rows = [{"id": str(i)} for i in range(10)]
        selected = choose_random_row(iter(rows), rng=random.Random(7))
        self.assertEqual(selected, {"id": "8"})

    def test_rejects_empty_dataset(self):
        with self.assertRaises(ValueError):
            choose_random_row(iter(()), rng=random.Random(7))


if __name__ == "__main__":
    unittest.main()
