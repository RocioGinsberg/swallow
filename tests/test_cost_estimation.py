from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.cost_estimation import estimate_cost, estimate_tokens


class CostEstimationTest(unittest.TestCase):
    def test_estimate_tokens_uses_local_approximation(self) -> None:
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcdefgh"), 2)

    def test_estimate_cost_uses_static_model_pricing(self) -> None:
        self.assertEqual(estimate_cost("local", 1000, 1000), 0.0)
        self.assertEqual(estimate_cost("codex", 1000, 1000), 0.0)
        self.assertAlmostEqual(estimate_cost("claude-3-5-sonnet", 1_000_000, 1_000_000), 18.0)
        self.assertEqual(estimate_cost("unknown-model", 1000, 1000), 0.0)


if __name__ == "__main__":
    unittest.main()
