"""Tests for pool_split.split_pool using Python standard library only."""

import itertools
import random
import unittest

from pool_split import split_pool


class TestSplitPool(unittest.TestCase):
    """Unit, exhaustive, and property-based tests for pool_split.split_pool."""

    def _assert_invariants(self, pool_cents: int, weights: list[int], result: list[int]) -> None:
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), len(weights))

        for val in result:
            self.assertIsInstance(val, int)
            self.assertNotIsInstance(val, bool)
            self.assertGreaterEqual(val, 0)

        # Hard rule: exact sum conservation
        self.assertEqual(sum(result), pool_cents)

        if pool_cents == 0:
            self.assertEqual(result, [0] * len(weights))
            return

        total = sum(weights)
        self.assertGreater(total, 0)

        for w, a in zip(weights, result):
            if w == 0:
                self.assertEqual(a, 0)
            # Exact integer Quota Rule: |a - pool_cents * w / total| < 1
            self.assertGreater(a * total, pool_cents * w - total)
            self.assertLess(a * total, pool_cents * w + total)

        # Weak monotonicity
        if len(weights) <= 50:
            for i in range(len(weights)):
                for j in range(i + 1, len(weights)):
                    if weights[i] > weights[j]:
                        self.assertGreaterEqual(result[i], result[j])
                    elif weights[i] < weights[j]:
                        self.assertLessEqual(result[i], result[j])
                    else:
                        self.assertLessEqual(abs(result[i] - result[j]), 1)

    def test_underpay_equal_three(self) -> None:
        result = split_pool(10000, [1, 1, 1])
        self._assert_invariants(10000, [1, 1, 1], result)

    def test_overpay_equal_three(self) -> None:
        result = split_pool(2, [1, 1, 1])
        self._assert_invariants(2, [1, 1, 1], result)

    def test_bankers_rounding_loss(self) -> None:
        result = split_pool(10, [1, 1, 1, 1])
        self._assert_invariants(10, [1, 1, 1, 1], result)

    def test_many_small_weights(self) -> None:
        for pool_cents, weights in [(1, [1] * 10), (5, [1] * 9)]:
            result = split_pool(pool_cents, weights)
            self._assert_invariants(pool_cents, weights, result)

    def test_large_integer_no_float_precision_loss(self) -> None:
        cases = [
            (10**18 + 1, [1, 1, 1]),
            (10**18 + 2, [1, 2, 3]),
        ]
        for pool_cents, weights in cases:
            result = split_pool(pool_cents, weights)
            self._assert_invariants(pool_cents, weights, result)

    def test_exact_tie_breaking_and_largest_remainder(self) -> None:
        self.assertEqual(split_pool(10000, [1, 1, 1]), [3334, 3333, 3333])
        self.assertEqual(split_pool(10, [1, 3]), [2, 8])
        self.assertEqual(split_pool(100, [1, 2, 5]), [12, 25, 63])
        self.assertEqual(split_pool(100, [1, 3, 6]), [10, 30, 60])

    def test_zero_weights_mixed(self) -> None:
        weights = [0, 1, 1, 0, 1]
        result = split_pool(10, weights)
        self._assert_invariants(10, weights, result)
        self.assertEqual(result[0], 0)
        self.assertEqual(result[3], 0)

    def test_zero_pool(self) -> None:
        self.assertEqual(split_pool(0, [1, 2, 3]), [0, 0, 0])
        self.assertEqual(split_pool(0, [0, 0]), [0, 0])
        self.assertEqual(split_pool(0, []), [])

    def test_single_user(self) -> None:
        self.assertEqual(split_pool(12345, [7]), [12345])

    def test_input_list_not_mutated(self) -> None:
        weights = [3, 1, 4, 1, 5]
        snapshot = list(weights)
        _ = split_pool(100, weights)
        self.assertEqual(weights, snapshot)

    def test_invalid_inputs(self) -> None:
        for pool_cents, weights in [
            (100, []),
            (100, [0, 0, 0]),
            (-1, [1, 2]),
            (100, [1, -1, 2]),
        ]:
            with self.subTest(pool_cents=pool_cents, weights=weights):
                with self.assertRaises(ValueError):
                    split_pool(pool_cents, weights)

        for pool_cents, weights in [
            (100.0, [1, 2]),
            (True, [1, 2]),
            (100, [1, 2.5]),
            (100, [1, False]),
        ]:
            with self.subTest(pool_cents=pool_cents, weights=weights):
                with self.assertRaises(TypeError):
                    split_pool(pool_cents, weights)

    def test_exhaustive_small_space(self) -> None:
        weight_tuples = [
            list(tup)
            for length in (1, 2, 3)
            for tup in itertools.product(range(0, 5), repeat=length)
            if sum(tup) > 0
        ]
        for pool_cents in range(0, 21):
            for weights in weight_tuples:
                result = split_pool(pool_cents, weights)
                self._assert_invariants(pool_cents, weights, result)

    def test_property_based_random_fuzz(self) -> None:
        rng = random.Random(20261122)
        for idx in range(2000):
            n = rng.randint(1, 100)
            mode = idx % 5
            if mode == 0:
                pool_cents = rng.randint(0, 50)
                weights = [rng.randint(1, 20) for _ in range(n)]
            elif mode == 1:
                pool_cents = rng.randint(100, 100000)
                weights = [rng.randint(1, 1000) for _ in range(n)]
            elif mode == 2:
                pool_cents = rng.randint(10**16, 10**18)
                weights = [rng.randint(1, 10**6) for _ in range(n)]
            elif mode == 3:
                pool_cents = rng.randint(0, 10000)
                w = rng.randint(1, 500)
                weights = [w] * n
            else:
                pool_cents = rng.randint(0, 50000)
                weights = [0 if rng.random() < 0.4 else rng.randint(1, 100000) for _ in range(n)]
                if sum(weights) == 0:
                    weights[rng.randrange(n)] = rng.randint(1, 100)

            result = split_pool(pool_cents, weights)
            self._assert_invariants(pool_cents, weights, result)


if __name__ == "__main__":
    unittest.main()
