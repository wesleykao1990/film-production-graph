from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from m4_rules import (  # noqa: E402
    ANCHOR_DEGRADED,
    ANCHOR_INTACT,
    CONDITION_A,
    CONDITION_B,
    evaluate_anchor_control,
    evaluate_dimension_requirement,
    evaluate_inconclusive_reuse,
    evaluate_mixed_repeat,
)


class M4RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import yaml

        cls.protocol = yaml.safe_load(
            (ROOT / "examples/evals/story-room-gate/protocol.yaml").read_text(
                encoding="utf-8"
            )
        )

    def test_per_brief_robustness_uses_only_stronger_aggregate_baseline(self) -> None:
        aggregate = {
            CONDITION_A: {"preference": 0.72},
            CONDITION_B: {"preference": 0.61},
        }
        per_brief = {
            "brief_1": {
                CONDITION_A: {"preference": 0.40},
                CONDITION_B: {"preference": 0.56},
            },
            "brief_2": {
                CONDITION_A: {"preference": 0.45},
                CONDITION_B: {"preference": 0.67},
            },
            "brief_3": {
                CONDITION_A: {"preference": 0.80},
                CONDITION_B: {"preference": 0.44},
            },
        }
        result = evaluate_dimension_requirement(
            aggregate=aggregate,
            per_brief=per_brief,
            threshold=0.60,
            per_brief_preference_floor=0.50,
            briefs_required=2,
        )
        self.assertEqual(result["stronger_baseline"], CONDITION_B)
        self.assertEqual(result["briefs_clearing_threshold"], 2)
        self.assertTrue(result["requirement_passed"])

    def test_aggregate_still_must_beat_both_baselines(self) -> None:
        aggregate = {
            CONDITION_A: {"preference": 0.80},
            CONDITION_B: {"preference": 0.59},
        }
        per_brief = {
            brief: {
                CONDITION_A: {"preference": 0.80},
                CONDITION_B: {"preference": 0.70},
            }
            for brief in ("brief_1", "brief_2", "brief_3")
        }
        result = evaluate_dimension_requirement(
            aggregate=aggregate,
            per_brief=per_brief,
            threshold=0.60,
            per_brief_preference_floor=0.50,
            briefs_required=2,
        )
        self.assertFalse(result["aggregate_against_both_passed"])
        self.assertFalse(result["requirement_passed"])

    def test_anchor_positive_control_passes_with_clear_intact_direction(self) -> None:
        choices = {
            "specificity": [ANCHOR_INTACT] * 5 + [ANCHOR_DEGRADED],
            "character_voice": [ANCHOR_INTACT] * 5 + [ANCHOR_DEGRADED],
            "causal_progression": [ANCHOR_INTACT] * 5 + [ANCHOR_DEGRADED],
        }
        result = evaluate_anchor_control(
            choices_by_dimension=choices,
            assigned_rater_count=6,
            protocol=self.protocol,
        )
        self.assertTrue(result["valid"])
        self.assertTrue(all(item["passed"] for item in result["per_dimension"].values()))

    def test_anchor_positive_control_failure_is_inconclusive(self) -> None:
        choices = {
            "specificity": [ANCHOR_INTACT, ANCHOR_DEGRADED] * 3,
            "character_voice": [ANCHOR_INTACT, ANCHOR_DEGRADED] * 3,
            "causal_progression": [ANCHOR_INTACT, ANCHOR_DEGRADED] * 3,
        }
        result = evaluate_anchor_control(
            choices_by_dimension=choices,
            assigned_rater_count=6,
            protocol=self.protocol,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["failure_outcome"], "INCONCLUSIVE")


    def test_anchor_tie_is_rejected_by_forced_choice_rule(self) -> None:
        choices = {
            "specificity": [ANCHOR_INTACT] * 5 + ["tie"],
            "character_voice": [ANCHOR_INTACT] * 6,
            "causal_progression": [ANCHOR_INTACT] * 6,
        }
        with self.assertRaises(ValueError):
            evaluate_anchor_control(
                choices_by_dimension=choices,
                assigned_rater_count=6,
                protocol=self.protocol,
            )

    def test_inconclusive_reuse_requires_every_attestation_and_safeguard(self) -> None:
        attestations = {
            key: True
            for key in self.protocol["inconclusive_rerun"]["attestations"]
        }
        result = evaluate_inconclusive_reuse(
            protocol=self.protocol,
            attestations=attestations,
            fresh_rater_pool=True,
            rerandomized_labels=True,
        )
        self.assertTrue(result["reuse_allowed"])
        self.assertEqual(result["sample_policy"], "reuse_frozen_primary_samples")

    def test_inconclusive_reuse_defaults_to_fresh_samples_when_evidence_is_uncertain(self) -> None:
        attestations = {
            key: True
            for key in self.protocol["inconclusive_rerun"]["attestations"]
        }
        attestations["unblinding_map_never_opened"] = None
        result = evaluate_inconclusive_reuse(
            protocol=self.protocol,
            attestations=attestations,
            fresh_rater_pool=True,
            rerandomized_labels=True,
        )
        self.assertFalse(result["reuse_allowed"])
        self.assertIn(
            "unblinding_map_never_opened", result["attestations_not_true"]
        )
        self.assertEqual(
            result["sample_policy"], "use_fresh_primary_briefs_and_samples"
        )

    def test_mixed_repeat_uses_primary_thresholds_and_non_regression_floor(self) -> None:
        aggregates = {
            "specificity": {
                CONDITION_A: {"preference": 0.65},
                CONDITION_B: {"preference": 0.60},
            },
            "character_voice": {
                CONDITION_A: {"preference": 0.55},
                CONDITION_B: {"preference": 0.52},
            },
            "causal_progression": {
                CONDITION_A: {"preference": 0.58},
                CONDITION_B: {"preference": 0.56},
            },
        }
        result = evaluate_mixed_repeat(
            aggregate_by_dimension=aggregates,
            affected_dimensions={"specificity", "causal_progression"},
            previously_passing_dimensions={"character_voice"},
            protocol=self.protocol,
            continuity_non_inferior=True,
            instrument_valid=True,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["decision"], "PASS")


if __name__ == "__main__":
    unittest.main()
