"""Pure M04 decision and instrument rules shared by analysis and simulation.

Keep this module free of file I/O. ``analyze_m4.py`` and ``simulate_m4.py``
import the same functions so the frozen preference rule, forced-choice
positive-control rule, and operating-characteristic calculation cannot silently
diverge.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

PRIMARY_DIMENSIONS = ("specificity", "character_voice", "causal_progression")
CONDITION_A = "equal_information"
CONDITION_B = "fixed_budget_conventional"
CONDITION_C = "story_room"
BASELINES = (CONDITION_A, CONDITION_B)

ANCHOR_INTACT = "intact"
ANCHOR_DEGRADED = "degraded"


def primary_thresholds(protocol: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the single threshold set used by every evidence-strength mode."""

    return protocol["pass_rule"]["primary"]


def select_stronger_baseline(aggregate: Mapping[str, Mapping[str, Any]]) -> str:
    """Select the baseline that is harder for Story Room in this dimension.

    "Stronger" means the comparison with the lower aggregate Story Room
    preference. A numerical tie is resolved in favour of the fixed-budget
    conventional workflow because it receives the larger frozen inference
    budget and is the more conservative deterministic tie-break.
    """

    values: dict[str, float] = {}
    for baseline in BASELINES:
        raw = aggregate[baseline].get("preference")
        if raw is None:
            raise ValueError(f"Missing aggregate preference for {baseline}")
        values[baseline] = float(raw)
    if values[CONDITION_B] <= values[CONDITION_A]:
        return CONDITION_B
    return CONDITION_A


def evaluate_dimension_requirement(
    *,
    aggregate: Mapping[str, Mapping[str, Any]],
    per_brief: Mapping[str, Mapping[str, Mapping[str, Any]]],
    threshold: float,
    per_brief_preference_floor: float,
    briefs_required: int,
) -> dict[str, Any]:
    """Evaluate one primary creative dimension under the v2.4 rule.

    Aggregate performance must clear the threshold against both baselines.
    Cross-brief robustness is checked only against the stronger aggregate
    baseline. Instrument validity is evaluated separately through blinded,
    forced-choice positive controls and never inferred from chance-corrected
    agreement on scored items.
    """

    stronger_baseline = select_stronger_baseline(aggregate)
    aggregate_passed = all(
        aggregate[baseline].get("preference") is not None
        and float(aggregate[baseline]["preference"]) >= threshold
        for baseline in BASELINES
    )

    briefs_clearing = 0
    per_brief_clear: dict[str, bool] = {}
    for brief_id, results in per_brief.items():
        value = results[stronger_baseline].get("preference")
        cleared = value is not None and float(value) > per_brief_preference_floor
        per_brief_clear[brief_id] = cleared
        briefs_clearing += int(cleared)

    requirement_passed = aggregate_passed and briefs_clearing >= briefs_required
    return {
        "threshold": threshold,
        "stronger_baseline": stronger_baseline,
        "stronger_baseline_preference": aggregate[stronger_baseline]["preference"],
        "aggregate_against_both_passed": aggregate_passed,
        "per_brief_baseline_policy": "stronger_aggregate_baseline",
        "per_brief_preference_floor": per_brief_preference_floor,
        "per_brief_comparison": "strictly_greater",
        "per_brief_clear": per_brief_clear,
        "briefs_clearing_threshold": briefs_clearing,
        "briefs_required": briefs_required,
        "requirement_passed": requirement_passed,
    }


def _anchor_counts(choices: Iterable[str]) -> dict[str, int]:
    counts = Counter(choices)
    return {
        "intact": counts[ANCHOR_INTACT],
        "degraded": counts[ANCHOR_DEGRADED],
        "total": counts[ANCHOR_INTACT] + counts[ANCHOR_DEGRADED],
    }


def evaluate_anchor_control(
    *,
    choices_by_dimension: Mapping[str, Iterable[str]],
    assigned_rater_count: int,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate the blinded, forced-choice positive-control anchors.

    The controls deliberately create a large, known quality contrast. They test
    whether the rating instrument and rater pool can recognize the three
    constructs directly. Anchor tasks do not offer a substantive tie option.
    A display or accessibility problem aborts and replaces the task before the
    rating dataset is frozen; it is not encoded as a tie or a creative judgment.

    Krippendorff's alpha and raw agreement on scored items remain diagnostics
    because chance-corrected agreement can collapse under skewed marginals even
    when raters consistently prefer one condition.
    """

    if assigned_rater_count < 1:
        raise ValueError("assigned_rater_count must be positive")

    config = protocol["instrument_validity"]["positive_control"]
    if config.get("response_mode") != "forced_choice":
        raise ValueError("Positive-control response_mode must be forced_choice")
    per_dimension_floor = float(config["per_dimension_intact_preference_floor"])
    pooled_minimum = float(config["pooled_intact_preference_minimum"])

    per_dimension: dict[str, Any] = {}
    pooled: list[str] = []
    allowed = {ANCHOR_INTACT, ANCHOR_DEGRADED}
    for dimension in PRIMARY_DIMENSIONS:
        values = list(choices_by_dimension.get(dimension, []))
        if len(values) != assigned_rater_count:
            raise ValueError(
                f"Anchor dimension {dimension} has {len(values)} judgments; "
                f"expected {assigned_rater_count}"
            )
        if any(value not in allowed for value in values):
            raise ValueError(
                f"Unknown or non-forced anchor choice in {dimension}; "
                "anchors permit intact/degraded only"
            )
        pooled.extend(values)
        counts = _anchor_counts(values)
        preference = counts["intact"] / counts["total"]
        direction_passed = preference > per_dimension_floor
        per_dimension[dimension] = {
            "counts": counts,
            "intact_preference": preference,
            "per_dimension_intact_preference_floor": per_dimension_floor,
            "comparison": "strictly_greater",
            "direction_passed": direction_passed,
            "passed": direction_passed,
        }

    pooled_counts = _anchor_counts(pooled)
    pooled_preference = pooled_counts["intact"] / pooled_counts["total"]
    pooled_passed = pooled_preference >= pooled_minimum
    valid = all(result["passed"] for result in per_dimension.values()) and pooled_passed

    return {
        "valid": valid,
        "failure_outcome": "INCONCLUSIVE",
        "response_mode": "forced_choice",
        "technical_issue_policy": "abort_replace_not_score",
        "assigned_rater_count": assigned_rater_count,
        "per_dimension": per_dimension,
        "pooled": {
            "counts": pooled_counts,
            "intact_preference": pooled_preference,
            "minimum_intact_preference": pooled_minimum,
            "passed": pooled_passed,
        },
    }


def evaluate_inconclusive_reuse(
    *,
    protocol: Mapping[str, Any],
    attestations: Mapping[str, bool | None],
    fresh_rater_pool: bool,
    rerandomized_labels: bool,
) -> dict[str, Any]:
    """Decide whether frozen primary samples may be re-rated after INCONCLUSIVE.

    Reuse is permitted only for an instrument-side failure where scored
    preferences remained withheld, the unblinding map was never opened, no
    creative authority inspected cross-condition outputs, and the creative
    pipeline is unchanged. A fresh rater pool and newly randomized opaque labels
    are mandatory. Missing or uncertain evidence defaults to fresh briefs and
    samples; this helper never infers an attestation from absence.
    """

    config = protocol["inconclusive_rerun"]
    required = tuple(config["attestations"].keys())
    missing = [key for key in required if key not in attestations]
    not_true = [key for key in required if attestations.get(key) is not True]
    safeguards = {
        "fresh_rater_pool": fresh_rater_pool,
        "rerandomized_labels": rerandomized_labels,
    }
    failed_safeguards = [key for key, value in safeguards.items() if value is not True]
    allowed = not missing and not not_true and not failed_safeguards
    return {
        "reuse_allowed": allowed,
        "new_protocol_version_required": bool(
            config["new_protocol_version_required"]
        ),
        "required_attestations": list(required),
        "missing_attestations": missing,
        "attestations_not_true": not_true,
        "failed_safeguards": failed_safeguards,
        "sample_policy": (
            "reuse_frozen_primary_samples"
            if allowed
            else str(config["if_any_attestation_unknown"])
        ),
    }


def classify_primary_decision(
    *,
    primary_passes: Mapping[str, bool],
    instrument_valid: bool,
    continuity_non_inferior: bool,
) -> str:
    """Classify the frozen primary-round result."""

    if not instrument_valid:
        return "INCONCLUSIVE"
    if all(primary_passes.values()) and continuity_non_inferior:
        return "PASS"
    if any(primary_passes.values()):
        return "MIXED"
    return "FAIL"


def evaluate_mixed_repeat(
    *,
    aggregate_by_dimension: Mapping[str, Mapping[str, Mapping[str, Any]]],
    affected_dimensions: set[str],
    previously_passing_dimensions: set[str],
    protocol: Mapping[str, Any],
    continuity_non_inferior: bool,
    instrument_valid: bool,
) -> dict[str, Any]:
    """Evaluate the reserve-brief repeat after a MIXED primary round.

    The repeat uses five fresh runs by default, the same aggregate thresholds,
    no extra per-brief hurdle, and a non-regression floor for dimensions that
    passed round one. Primary-round anchor validity is inherited when the same
    qualified rater pool and instrument are used. New raters must complete the
    anchors before ``instrument_valid`` may be true.
    """

    thresholds = primary_thresholds(protocol)
    floor = float(protocol["mixed_repeat"]["previously_passing_dimension_floor"])
    dimension_results: dict[str, Any] = {}

    for dimension in PRIMARY_DIMENSIONS:
        aggregates = aggregate_by_dimension[dimension]
        if dimension in affected_dimensions:
            threshold = float(thresholds[dimension])
            passed = all(
                aggregates[baseline].get("preference") is not None
                and float(aggregates[baseline]["preference"]) >= threshold
                for baseline in BASELINES
            )
            role = "affected"
        elif dimension in previously_passing_dimensions:
            threshold = floor
            passed = all(
                aggregates[baseline].get("preference") is not None
                and float(aggregates[baseline]["preference"]) >= floor
                for baseline in BASELINES
            )
            role = "non_regression"
        else:
            threshold = floor
            passed = True
            role = "diagnostic"
        dimension_results[dimension] = {
            "role": role,
            "threshold": threshold,
            "passed": passed,
        }

    passed = (
        instrument_valid
        and continuity_non_inferior
        and all(result["passed"] for result in dimension_results.values())
    )
    return {
        "passed": passed,
        "decision": "PASS" if passed else ("INCONCLUSIVE" if not instrument_valid else "FAIL"),
        "dimension_results": dimension_results,
        "continuity_non_inferior": continuity_non_inferior,
        "instrument_valid": instrument_valid,
    }
