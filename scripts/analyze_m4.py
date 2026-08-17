#!/usr/bin/env python3
"""Analyze an M04a Story Room gate run.

This implements the frozen internal decision heuristic in
``docs/M4_EXPERIMENT_PROTOCOL.md``. It intentionally does not report p-values
or claim statistical significance. Blinded positive-control anchors validate
the rating instrument before scored preferences are exposed; agreement
statistics on scored items are diagnostics only.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml

from m4_rules import (
    ANCHOR_DEGRADED,
    ANCHOR_INTACT,
    BASELINES,
    CONDITION_A,
    CONDITION_B,
    CONDITION_C,
    PRIMARY_DIMENSIONS,
    classify_primary_decision,
    evaluate_anchor_control,
    evaluate_dimension_requirement,
    primary_thresholds,
)

CHOICE_C = "story_room"
CHOICE_BASELINE = "baseline"
CHOICE_TIE = "tie"


class AnalysisError(ValueError):
    """Raised when inputs violate the frozen analysis contract."""


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AnalysisError(f"Expected mapping in {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AnalysisError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(item, dict):
            raise AnalysisError(f"Expected object at {path}:{line_number}")
        records.append(item)
    if not records:
        raise AnalysisError(f"No rating records in {path}")
    return records


def build_manifest_index(
    manifest: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, dict[str, Any]]]:
    triplets = manifest.get("triplets")
    if not isinstance(triplets, list) or len(triplets) != 9:
        raise AnalysisError("Run manifest must contain exactly nine scored triplets")

    triplet_index: dict[str, dict[str, Any]] = {}
    sample_index: dict[str, dict[str, str]] = {}
    for triplet in triplets:
        triplet_id = str(triplet["triplet_id"])
        if triplet_id in triplet_index:
            raise AnalysisError(f"Duplicate triplet_id: {triplet_id}")
        samples = triplet.get("samples", [])
        if len(samples) != 3:
            raise AnalysisError(f"{triplet_id} must contain exactly three samples")
        conditions = [sample["condition"] for sample in samples]
        if set(conditions) != {CONDITION_A, CONDITION_B, CONDITION_C}:
            raise AnalysisError(f"{triplet_id} must contain one sample for each condition")
        for sample in samples:
            sample_id = str(sample["sample_id"])
            if sample_id in sample_index:
                raise AnalysisError(f"Duplicate sample_id: {sample_id}")
            sample_index[sample_id] = {
                "triplet_id": triplet_id,
                "condition": str(sample["condition"]),
            }
        triplet_index[triplet_id] = triplet

    raw_anchor_tasks = manifest.get("anchor_tasks")
    if not isinstance(raw_anchor_tasks, list) or not raw_anchor_tasks:
        raise AnalysisError("Run manifest must contain blinded positive-control anchor_tasks")
    anchor_index: dict[str, dict[str, Any]] = {}
    covered_dimensions: list[str] = []
    for task in raw_anchor_tasks:
        anchor_id = str(task["anchor_id"])
        if anchor_id in anchor_index:
            raise AnalysisError(f"Duplicate anchor_id: {anchor_id}")
        dimensions = [str(value) for value in task.get("dimensions", [])]
        if not dimensions or any(value not in PRIMARY_DIMENSIONS for value in dimensions):
            raise AnalysisError(f"Invalid anchor dimensions for {anchor_id}: {dimensions}")
        if len(set(dimensions)) != len(dimensions):
            raise AnalysisError(f"Duplicate dimensions in anchor {anchor_id}")
        left_id = str(task["left_sample_id"])
        right_id = str(task["right_sample_id"])
        intact_id = str(task["intact_sample_id"])
        degraded_id = str(task["degraded_sample_id"])
        if {left_id, right_id} != {intact_id, degraded_id}:
            raise AnalysisError(f"Anchor {anchor_id} left/right mapping does not match roles")
        anchor_index[anchor_id] = {
            **task,
            "dimensions": dimensions,
            "left_sample_id": left_id,
            "right_sample_id": right_id,
            "intact_sample_id": intact_id,
            "degraded_sample_id": degraded_id,
        }
        covered_dimensions.extend(dimensions)
    if Counter(covered_dimensions) != Counter(PRIMARY_DIMENSIONS):
        raise AnalysisError(
            "Anchor tasks must cover each primary dimension exactly once; got "
            f"{covered_dimensions}"
        )

    return triplet_index, sample_index, anchor_index


def expected_ratings_per_triplet(run_mode: str, protocol: dict[str, Any]) -> int:
    raters = protocol["raters"]
    if run_mode in {"standard_seven", "standard_six", "standard_five"}:
        return int(raters["standard_ratings_per_triplet"])
    if run_mode == "degraded_three":
        return int(raters["degraded_ratings_per_triplet"])
    raise AnalysisError(f"Unknown run_mode: {run_mode}")


def normalize_pairwise_choice(
    rating: dict[str, Any],
    *,
    triplet_id: str,
    sample_index: dict[str, dict[str, str]],
) -> tuple[str, str]:
    left_id = str(rating["left_sample_id"])
    right_id = str(rating["right_sample_id"])
    if left_id not in sample_index or right_id not in sample_index:
        raise AnalysisError(f"Unknown sample in rating pair {left_id} vs {right_id}")
    left = sample_index[left_id]
    right = sample_index[right_id]
    if left["triplet_id"] != triplet_id or right["triplet_id"] != triplet_id:
        raise AnalysisError(f"Rating pair crosses triplets in {triplet_id}")

    conditions = {left["condition"], right["condition"]}
    if CONDITION_C not in conditions or len(conditions & set(BASELINES)) != 1:
        raise AnalysisError(
            f"Each gating pair must compare Story Room with one baseline; got {conditions}"
        )
    baseline = next(iter(conditions & set(BASELINES)))

    choice = rating["choice"]
    if choice == "tie":
        return baseline, CHOICE_TIE
    if choice not in {"left", "right"}:
        raise AnalysisError(f"Unknown pairwise choice: {choice}")
    selected_id = left_id if choice == "left" else right_id
    selected_condition = sample_index[selected_id]["condition"]
    return baseline, CHOICE_C if selected_condition == CONDITION_C else CHOICE_BASELINE


def normalize_anchor_choice(
    rating: dict[str, Any], *, task: dict[str, Any]
) -> str:
    left_id = str(rating["left_sample_id"])
    right_id = str(rating["right_sample_id"])
    if left_id != task["left_sample_id"] or right_id != task["right_sample_id"]:
        raise AnalysisError(
            f"Anchor {task['anchor_id']} rating uses an unexpected sample order"
        )
    choice = rating["choice"]
    if choice not in {"left", "right"}:
        raise AnalysisError(
            f"Unknown anchor choice: {choice}; positive-control anchors are forced choice"
        )
    selected_id = left_id if choice == "left" else right_id
    return ANCHOR_INTACT if selected_id == task["intact_sample_id"] else ANCHOR_DEGRADED


def validate_and_normalize_ratings(
    records: list[dict[str, Any]],
    *,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    triplet_index: dict[str, dict[str, Any]],
    sample_index: dict[str, dict[str, str]],
    anchor_index: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[str], list[str], dict[str, float]]:
    run_mode = str(manifest["run_mode"])
    expected_per_triplet = expected_ratings_per_triplet(run_mode, protocol)
    primary_records = [record for record in records if record.get("record_type") == "triplet"]
    anchor_records = [record for record in records if record.get("record_type") == "anchor"]
    unknown_types = [record.get("record_type") for record in records if record.get("record_type") not in {"triplet", "anchor"}]
    if unknown_types:
        raise AnalysisError(f"Unknown rating record types: {unknown_types}")

    seen_rater_triplet: set[tuple[str, str]] = set()
    coverage: Counter[str] = Counter()
    normalized: list[dict[str, Any]] = []
    warnings: list[str] = []

    for record in primary_records:
        rater_id = str(record["rater_id"])
        triplet_id = str(record["triplet_id"])
        if triplet_id not in triplet_index:
            raise AnalysisError(f"Unknown triplet_id: {triplet_id}")
        key = (rater_id, triplet_id)
        if key in seen_rater_triplet:
            raise AnalysisError(f"Duplicate rater/triplet record: {key}")
        seen_rater_triplet.add(key)
        coverage[triplet_id] += 1
        triplet = triplet_index[triplet_id]
        if str(record["brief_id"]) != str(triplet["brief_id"]):
            raise AnalysisError(f"Brief mismatch for {rater_id}/{triplet_id}")
        if int(record["run_index"]) != int(triplet["run_index"]):
            raise AnalysisError(f"Run-index mismatch for {rater_id}/{triplet_id}")

        primary = record.get("primary_ratings")
        if not isinstance(primary, list) or len(primary) != 6:
            raise AnalysisError(f"{rater_id}/{triplet_id} must contain six primary ratings")
        pair_dimension_keys: set[tuple[str, str]] = set()
        for rating in primary:
            dimension = str(rating["dimension"])
            if dimension not in PRIMARY_DIMENSIONS:
                raise AnalysisError(f"Non-primary dimension in primary_ratings: {dimension}")
            baseline, normalized_choice = normalize_pairwise_choice(
                rating, triplet_id=triplet_id, sample_index=sample_index
            )
            dim_key = (dimension, baseline)
            if dim_key in pair_dimension_keys:
                raise AnalysisError(
                    f"Duplicate {dimension}/{baseline} judgment for {rater_id}/{triplet_id}"
                )
            pair_dimension_keys.add(dim_key)
            normalized.append(
                {
                    "rater_id": rater_id,
                    "triplet_id": triplet_id,
                    "brief_id": str(triplet["brief_id"]),
                    "run_index": int(triplet["run_index"]),
                    "dimension": dimension,
                    "baseline": baseline,
                    "choice": normalized_choice,
                }
            )

        expected_keys = {
            (dimension, baseline)
            for dimension in PRIMARY_DIMENSIONS
            for baseline in BASELINES
        }
        if pair_dimension_keys != expected_keys:
            missing = expected_keys - pair_dimension_keys
            raise AnalysisError(
                f"Missing primary judgments for {rater_id}/{triplet_id}: {sorted(missing)}"
            )

        duration = int(record["duration_seconds"])
        if duration <= 0:
            raise AnalysisError(f"Invalid duration for {rater_id}/{triplet_id}")

    for triplet_id in sorted(triplet_index):
        if coverage[triplet_id] != expected_per_triplet:
            raise AnalysisError(
                f"{triplet_id} has {coverage[triplet_id]} ratings; expected {expected_per_triplet}"
            )

    primary_rater_ids = sorted({str(record["rater_id"]) for record in primary_records})
    if run_mode == "standard_seven" and len(primary_rater_ids) < 7:
        raise AnalysisError("standard_seven requires at least seven completed raters")
    if run_mode == "standard_six" and len(primary_rater_ids) < 6:
        raise AnalysisError("standard_six requires at least six completed raters")
    if run_mode == "standard_five" and len(primary_rater_ids) < 5:
        raise AnalysisError("standard_five requires at least five completed raters")
    if run_mode == "degraded_three" and len(primary_rater_ids) != 3:
        raise AnalysisError("degraded_three requires exactly three completed raters")

    max_allowed = (
        int(protocol["raters"]["max_triplets_per_rater_with_seven"])
        if run_mode == "standard_seven"
        else int(protocol["raters"]["max_triplets_per_rater_with_six"])
        if run_mode == "standard_six"
        else int(protocol["raters"]["max_triplets_per_rater_with_five"])
        if run_mode == "standard_five"
        else int(protocol["raters"]["max_triplets_per_rater_degraded"])
    )
    rater_load = Counter(str(record["rater_id"]) for record in primary_records)
    overloaded = {r: n for r, n in rater_load.items() if n > max_allowed}
    if overloaded:
        raise AnalysisError(f"Rater workload exceeds frozen maximum: {overloaded}")

    # Every scored rater must complete every anchor. No anchor-only rater can
    # influence the instrument check.
    seen_anchor: set[tuple[str, str]] = set()
    anchor_choices_by_dimension: dict[str, list[str]] = defaultdict(list)
    for record in anchor_records:
        rater_id = str(record["rater_id"])
        anchor_id = str(record["anchor_id"])
        if rater_id not in primary_rater_ids:
            raise AnalysisError(f"Anchor-only rater is not allowed: {rater_id}")
        if anchor_id not in anchor_index:
            raise AnalysisError(f"Unknown anchor_id: {anchor_id}")
        key = (rater_id, anchor_id)
        if key in seen_anchor:
            raise AnalysisError(f"Duplicate anchor rating: {key}")
        seen_anchor.add(key)
        task = anchor_index[anchor_id]
        ratings = record.get("anchor_ratings")
        if not isinstance(ratings, list):
            raise AnalysisError(f"Anchor {anchor_id} ratings must be an array")
        dimensions_seen: set[str] = set()
        for rating in ratings:
            dimension = str(rating["dimension"])
            if dimension not in task["dimensions"]:
                raise AnalysisError(
                    f"Anchor {anchor_id} does not target dimension {dimension}"
                )
            if dimension in dimensions_seen:
                raise AnalysisError(
                    f"Duplicate {dimension} judgment for {rater_id}/{anchor_id}"
                )
            dimensions_seen.add(dimension)
            anchor_choices_by_dimension[dimension].append(
                normalize_anchor_choice(rating, task=task)
            )
        if dimensions_seen != set(task["dimensions"]):
            raise AnalysisError(
                f"Anchor {anchor_id} missing targeted dimensions for {rater_id}: "
                f"{sorted(set(task['dimensions']) - dimensions_seen)}"
            )
        if int(record["duration_seconds"]) <= 0:
            raise AnalysisError(f"Invalid anchor duration for {rater_id}/{anchor_id}")

    expected_anchor_pairs = {
        (rater_id, anchor_id)
        for rater_id in primary_rater_ids
        for anchor_id in anchor_index
    }
    if seen_anchor != expected_anchor_pairs:
        missing = sorted(expected_anchor_pairs - seen_anchor)
        extra = sorted(seen_anchor - expected_anchor_pairs)
        raise AnalysisError(f"Anchor coverage mismatch; missing={missing}, extra={extra}")

    target_seconds = int(protocol["presentation"]["target_minutes_per_rater_max"]) * 60
    total_duration: Counter[str] = Counter()
    for record in records:
        total_duration[str(record["rater_id"])] += int(record["duration_seconds"])
    over_time = {r: seconds for r, seconds in total_duration.items() if seconds > target_seconds}
    if over_time:
        warnings.append(
            "One or more raters exceeded the target completion time, including anchors: "
            + ", ".join(
                f"{r}={seconds / 60:.1f}m" for r, seconds in sorted(over_time.items())
            )
        )

    return (
        normalized,
        dict(anchor_choices_by_dimension),
        warnings,
        primary_rater_ids,
        {rater: seconds / 60 for rater, seconds in total_duration.items()},
    )


def raw_pairwise_agreement(items: dict[tuple[str, str], list[str]]) -> float | None:
    agreeing = 0
    total = 0
    for choices in items.values():
        for left, right in itertools.combinations(choices, 2):
            total += 1
            agreeing += int(left == right)
    return agreeing / total if total else None


def krippendorff_alpha_nominal(items: dict[tuple[str, str], list[str]]) -> float | None:
    """Compute nominal Krippendorff alpha as a diagnostic, never a hard gate."""

    coincidence: dict[str, Counter[str]] = defaultdict(Counter)
    total_coincidences = 0.0
    for choices in items.values():
        m = len(choices)
        if m < 2:
            continue
        counts = Counter(choices)
        for c, n_c in counts.items():
            for c2, n_c2 in counts.items():
                value = (
                    n_c * (n_c - 1) / (m - 1)
                    if c == c2
                    else n_c * n_c2 / (m - 1)
                )
                coincidence[c][c2] += value
                total_coincidences += value
    if total_coincidences <= 1:
        return None

    observed_disagreement = 0.0
    marginals: Counter[str] = Counter()
    for c, row in coincidence.items():
        for c2, value in row.items():
            marginals[c] += value
            if c != c2:
                observed_disagreement += value
    observed_disagreement /= total_coincidences

    expected_agreement_numerator = sum(n_c * (n_c - 1) for n_c in marginals.values())
    expected_agreement = expected_agreement_numerator / (
        total_coincidences * (total_coincidences - 1)
    )
    expected_disagreement = 1.0 - expected_agreement
    if expected_disagreement <= 0:
        return 1.0 if observed_disagreement == 0 else None
    return 1.0 - observed_disagreement / expected_disagreement


def preference_fraction(choices: Iterable[str]) -> tuple[float | None, dict[str, int]]:
    counts = Counter(choices)
    denominator = counts[CHOICE_C] + counts[CHOICE_BASELINE]
    fraction = counts[CHOICE_C] / denominator if denominator else None
    return fraction, {
        "story_room": counts[CHOICE_C],
        "baseline": counts[CHOICE_BASELINE],
        "ties": counts[CHOICE_TIE],
        "non_tie_denominator": denominator,
    }


def rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def summarize_cost_continuity(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    sample_rows = [
        sample
        for triplet in manifest["triplets"]
        for sample in triplet["samples"]
        if sample["valid"]
    ]
    condition_samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in sample_rows:
        condition_samples[str(sample["condition"])].append(sample)

    means: dict[str, float] = {}
    for condition in (CONDITION_A, CONDITION_B, CONDITION_C):
        samples = condition_samples[condition]
        if not samples:
            raise AnalysisError(f"No valid samples for {condition}")
        means[condition] = sum(
            float(sample["hard_violation_count"]) for sample in samples
        ) / len(samples)
    best_baseline_mean = min(means[CONDITION_A], means[CONDITION_B])
    continuity_non_inferior = means[CONDITION_C] <= best_baseline_mean
    continuity = {
        "mean_hard_violations_by_condition": {k: rounded(v) for k, v in means.items()},
        "best_baseline_mean": rounded(best_baseline_mean),
        "story_room_mean": rounded(means[CONDITION_C]),
        "non_inferior": continuity_non_inferior,
    }

    cost_latency: dict[str, Any] = {}
    for condition in (CONDITION_A, CONDITION_B, CONDITION_C):
        samples = condition_samples[condition]
        costs = [float(sample["cost_usd"]) for sample in samples]
        latencies = [float(sample["latency_seconds"]) for sample in samples]
        cost_latency[condition] = {
            "sample_count": len(samples),
            "total_cost_usd": rounded(sum(costs), 6),
            "mean_cost_usd": rounded(sum(costs) / len(costs), 6),
            "mean_latency_seconds": rounded(sum(latencies) / len(latencies), 2),
        }
    c_total = cost_latency[CONDITION_C]["total_cost_usd"]
    b_total = cost_latency[CONDITION_B]["total_cost_usd"]
    cost_latency["actual_B_to_C_cost_ratio"] = rounded(
        b_total / c_total if c_total else None
    )
    return continuity, cost_latency


def analyze(
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    triplet_index, sample_index, anchor_index = build_manifest_index(manifest)
    (
        normalized,
        anchor_choices,
        warnings,
        rater_ids,
        minutes_by_rater,
    ) = validate_and_normalize_ratings(
        records,
        protocol=protocol,
        manifest=manifest,
        triplet_index=triplet_index,
        sample_index=sample_index,
        anchor_index=anchor_index,
    )

    run_mode = str(manifest["run_mode"])
    evidence_strength = (
        "degraded_rater_diversity" if run_mode == "degraded_three" else "standard"
    )
    instrument_check = evaluate_anchor_control(
        choices_by_dimension=anchor_choices,
        assigned_rater_count=len(rater_ids),
        protocol=protocol,
    )

    # Agreement on scored items remains visible for diagnosis but cannot by
    # itself make the run INCONCLUSIVE. This avoids the alpha/prevalence paradox.
    reliability_diagnostics: dict[str, Any] = {}
    for dimension in PRIMARY_DIMENSIONS:
        dim_rows = [row for row in normalized if row["dimension"] == dimension]
        units: dict[tuple[str, str], list[str]] = defaultdict(list)
        for row in dim_rows:
            units[(row["triplet_id"], row["baseline"])].append(row["choice"])
        raw = raw_pairwise_agreement(units)
        alpha = krippendorff_alpha_nominal(units)
        tie_count = sum(row["choice"] == CHOICE_TIE for row in dim_rows)
        reliability_diagnostics[dimension] = {
            "raw_pairwise_agreement": rounded(raw),
            "krippendorff_alpha_nominal": rounded(alpha),
            "tie_rate": rounded(tie_count / len(dim_rows) if dim_rows else None),
            "gating": False,
        }

    continuity, cost_latency = summarize_cost_continuity(manifest)

    # The anchor check is read first. If it fails, scored preference results are
    # withheld rather than used to tune skills under a broken instrument.
    preferences: dict[str, Any] | None = None
    primary_passes: dict[str, bool] | None = None
    if instrument_check["valid"]:
        thresholds = primary_thresholds(protocol)
        preferences = {}
        primary_passes = {}
        for dimension in PRIMARY_DIMENSIONS:
            dim_rows = [row for row in normalized if row["dimension"] == dimension]
            aggregate: dict[str, Any] = {}
            per_brief: dict[str, Any] = defaultdict(dict)
            for baseline in BASELINES:
                baseline_rows = [row for row in dim_rows if row["baseline"] == baseline]
                fraction, counts = preference_fraction(
                    row["choice"] for row in baseline_rows
                )
                aggregate[baseline] = {"preference": rounded(fraction), "counts": counts}
                for brief_id in sorted({row["brief_id"] for row in baseline_rows}):
                    brief_rows = [
                        row for row in baseline_rows if row["brief_id"] == brief_id
                    ]
                    brief_fraction, brief_counts = preference_fraction(
                        row["choice"] for row in brief_rows
                    )
                    per_brief[brief_id][baseline] = {
                        "preference": rounded(brief_fraction),
                        "counts": brief_counts,
                    }

            threshold = float(thresholds[dimension])
            rule_result = evaluate_dimension_requirement(
                aggregate=aggregate,
                per_brief=per_brief,
                threshold=threshold,
                per_brief_preference_floor=float(
                    protocol["pass_rule"]["per_brief_preference_floor"]
                ),
                briefs_required=int(
                    thresholds["briefs_required_to_clear_each_primary"]
                ),
            )
            primary_passes[dimension] = bool(rule_result["requirement_passed"])
            preferences[dimension] = {
                "threshold": threshold,
                "against_equal_information": aggregate[CONDITION_A],
                "against_fixed_budget_conventional": aggregate[CONDITION_B],
                "per_brief": dict(per_brief),
                **rule_result,
            }

    decision = classify_primary_decision(
        primary_passes=primary_passes or {dimension: False for dimension in PRIMARY_DIMENSIONS},
        instrument_valid=bool(instrument_check["valid"]),
        continuity_non_inferior=bool(continuity["non_inferior"]),
    )

    triplet_load = Counter(
        str(record["rater_id"])
        for record in records
        if record.get("record_type") == "triplet"
    )
    anchor_load = Counter(
        str(record["rater_id"])
        for record in records
        if record.get("record_type") == "anchor"
    )

    return {
        "analysis_version": "2.4.0",
        "decision_mode": "exploratory_product_heuristic",
        "run_mode": run_mode,
        "evidence_strength": evidence_strength,
        "decision": decision,
        "rater_count": len(rater_ids),
        "rater_workload": {
            "triplets_by_rater": dict(triplet_load),
            "anchor_tasks_by_rater": dict(anchor_load),
            "minutes_by_rater": {
                rater: rounded(minutes, 2) for rater, minutes in minutes_by_rater.items()
            },
        },
        "instrument_check": instrument_check,
        "reliability_diagnostics": reliability_diagnostics,
        "preference_results_withheld": not bool(instrument_check["valid"]),
        "preferences": preferences,
        "primary_requirements": primary_passes,
        "mixed_repeat_plan": {
            "eligible": decision == "MIXED",
            "affected_dimensions": [
                dimension
                for dimension, passed in (primary_passes or {}).items()
                if not passed
            ],
            "previously_passing_dimensions": [
                dimension
                for dimension, passed in (primary_passes or {}).items()
                if passed
            ],
            "runs_per_condition": int(protocol["mixed_repeat"]["runs_per_condition"]),
            "threshold_policy": "same_as_primary_aggregate",
            "round_one_pooling": "report_separately_do_not_pool",
            "instrument_policy": "inherit_if_same_rater_pool_else_repeat_anchors",
        },
        "continuity": continuity,
        "cost_latency": cost_latency,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ratings", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        protocol = load_yaml(args.protocol)
        manifest = load_yaml(args.manifest)
        expected_protocol_hash = "sha256:" + hashlib.sha256(
            args.protocol.read_bytes()
        ).hexdigest()
        if manifest.get("protocol_hash") != expected_protocol_hash:
            raise AnalysisError(
                "Run manifest protocol_hash does not match the supplied protocol file"
            )
        report = analyze(protocol, manifest, load_jsonl(args.ratings))
    except (AnalysisError, KeyError, TypeError, ValueError) as exc:
        print(f"M04 analysis failed: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
