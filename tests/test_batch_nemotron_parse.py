import random
import unittest

from src.batch_nemotron_parse import sample_rows


class SampleRowsTests(unittest.TestCase):
    def test_returns_requested_number_without_replacement(self):
        rows = [{"id": str(i)} for i in range(20)]
        selected = sample_rows(rows, 5, rng=random.Random(42))
        self.assertEqual(len(selected), 5)
        self.assertEqual(len({row["id"] for row in selected}), 5)

    def test_rejects_too_small_iterable(self):
        with self.assertRaises(ValueError):
            sample_rows([{"id": "1"}], 2, rng=random.Random(42))


if __name__ == "__main__":
    unittest.main()
