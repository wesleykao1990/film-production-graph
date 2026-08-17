from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from simulate_m4 import assignment_for_mode, load_yaml, simulate_point  # noqa: E402


class SimulateM4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        base = ROOT / "examples" / "evals" / "story-room-gate"
        cls.protocol = load_yaml(base / "protocol.yaml")
        cls.plan = load_yaml(base / "assignment-plan.example.yaml")

    def _kwargs(self, *, reliability_mode: str = "simulate") -> dict:
        _, assignments = assignment_for_mode(self.plan, "standard_six")
        return {
            "seed": 42,
            "trials": 80,
            "true_preference": 0.70,
            "protocol": self.protocol,
            "assignments": assignments,
            "tie_rate": 0.15,
            "rater_sd_logit": 0.30,
            "brief_sd_logit": 0.35,
            "dimension_sd_logit": 0.15,
            "run_sd_logit": 0.15,
            "continuity_pass_probability": 1.0,
            "reliability_mode": reliability_mode,
            "anchor_true_preference": 0.90,
            "anchor_rater_sd_logit": 0.30,
            "anchor_dimension_sd_logit": 0.10,
        }

    def test_probabilities_are_deterministic_and_normalized(self) -> None:
        kwargs = self._kwargs()
        first = simulate_point(**kwargs)
        second = simulate_point(**kwargs)
        self.assertEqual(first, second)
        probabilities = first["primary_decision_probabilities"]
        self.assertAlmostEqual(sum(probabilities.values()), 1.0, places=4)
        self.assertGreaterEqual(
            first["eventual_pass_probability"], probabilities["PASS"]
        )
        self.assertEqual(first["mixed_repeat_runs_per_condition"], 5)

    def test_simulated_instrument_exercises_inconclusive_branch(self) -> None:
        kwargs = self._kwargs(reliability_mode="simulate")
        kwargs.update(
            trials=150,
            anchor_true_preference=0.70,
            anchor_rater_sd_logit=0.60,
        )
        result = simulate_point(**kwargs)
        inconclusive = result["primary_decision_probabilities"]["INCONCLUSIVE"]
        self.assertGreater(inconclusive, 0.0)
        self.assertLess(inconclusive, 1.0)


    def test_forced_choice_anchor_has_no_tie_ceiling_for_near_perfect_raters(self) -> None:
        kwargs = self._kwargs(reliability_mode="simulate")
        kwargs.update(
            trials=500,
            anchor_true_preference=0.98,
            anchor_rater_sd_logit=0.0,
            anchor_dimension_sd_logit=0.0,
        )
        result = simulate_point(**kwargs)
        self.assertGreater(result["instrument_pass_probability"], 0.98)

    def test_assume_interpretable_is_diagnostic_only_and_has_no_inconclusive(self) -> None:
        result = simulate_point(**self._kwargs(reliability_mode="assume_interpretable"))
        self.assertEqual(result["primary_decision_probabilities"]["INCONCLUSIVE"], 0.0)
        self.assertEqual(result["instrument_pass_probability"], 1.0)

    def test_degraded_mode_buys_full_triplet_coverage(self) -> None:
        _, assignments = assignment_for_mode(self.plan, "degraded_three")
        self.assertEqual(len(assignments), 9)
        self.assertTrue(all(len(raters) == 3 for raters in assignments.values()))
        self.assertEqual(
            {rater for raters in assignments.values() for rater in raters},
            {"R1", "R2", "R3"},
        )


if __name__ == "__main__":
    unittest.main()
