#!/usr/bin/env python3
"""Simulate operating characteristics of the frozen M04 decision rule.

This is not a power calculator for a scientific efficacy claim. It is a
pre-freeze product-risk check that estimates PASS, MIXED, FAIL, and
INCONCLUSIVE probabilities under declared assumptions.

The default ``--reliability-mode simulate`` exercises the blinded, forced-choice
anchor-based instrument check. ``assume_interpretable`` exists only to isolate preference
rule behavior and cannot satisfy the real freeze checklist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

import yaml

from analyze_m4 import (
    krippendorff_alpha_nominal,
    preference_fraction,
    raw_pairwise_agreement,
)
from m4_rules import (
    ANCHOR_DEGRADED,
    ANCHOR_INTACT,
    BASELINES,
    PRIMARY_DIMENSIONS,
    classify_primary_decision,
    evaluate_anchor_control,
    evaluate_dimension_requirement,
    evaluate_mixed_repeat,
    primary_thresholds,
)

CHOICE_C = "story_room"
CHOICE_BASELINE = "baseline"
CHOICE_TIE = "tie"
BRIEF_IDS = ("brief_1", "brief_2", "brief_3")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def logit(p: float) -> float:
    if not 0 < p < 1:
        raise ValueError("Preference must be strictly between zero and one")
    return math.log(p / (1.0 - p))


def logistic(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def assignment_for_mode(
    plan: dict[str, Any], run_mode: str
) -> tuple[str, dict[str, list[str]]]:
    mapping = {
        "standard_seven": "standard_timing_fallback_seven_raters",
        "standard_six": "standard_target_six_raters",
        "standard_five": "standard_fallback_five_raters",
        "degraded_three": "degraded_three_rater_mode",
    }
    try:
        key = mapping[run_mode]
        raw = plan[key]["triplets"]
    except KeyError as exc:
        raise ValueError(f"Assignment plan does not support {run_mode}") from exc
    return key, {
        str(triplet): [str(rater) for rater in raters]
        for triplet, raters in raw.items()
    }


def rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def draw_choice(rng: random.Random, probability: float, tie_rate: float) -> str:
    if rng.random() < tie_rate:
        return CHOICE_TIE
    return CHOICE_C if rng.random() < probability else CHOICE_BASELINE


def draw_anchor_choice(rng: random.Random, probability: float) -> str:
    """Draw a forced-choice positive-control judgment."""

    return ANCHOR_INTACT if rng.random() < probability else ANCHOR_DEGRADED


def simulate_anchor_check(
    *,
    rng: random.Random,
    rater_ids: list[str],
    protocol: dict[str, Any],
    anchor_true_preference: float,
    anchor_rater_sd_logit: float,
    anchor_dimension_sd_logit: float,
    reliability_mode: str,
) -> dict[str, Any]:
    if reliability_mode == "assume_interpretable":
        return {
            "valid": True,
            "mode": "assume_interpretable",
            "per_dimension": {},
            "pooled": {},
        }

    base = logit(anchor_true_preference)
    rater_effects = {
        rater: rng.gauss(0.0, anchor_rater_sd_logit) for rater in rater_ids
    }
    choices_by_dimension: dict[str, list[str]] = {}
    for dimension in PRIMARY_DIMENSIONS:
        dimension_effect = rng.gauss(0.0, anchor_dimension_sd_logit)
        values = []
        for rater in rater_ids:
            probability = logistic(base + rater_effects[rater] + dimension_effect)
            values.append(draw_anchor_choice(rng, probability))
        choices_by_dimension[dimension] = values

    result = evaluate_anchor_control(
        choices_by_dimension=choices_by_dimension,
        assigned_rater_count=len(rater_ids),
        protocol=protocol,
    )
    result["mode"] = "simulate"
    return result


def summarize_dimension(
    *,
    choices: dict[tuple[str, str], list[str]],
    triplet_briefs: dict[str, str],
    protocol: dict[str, Any],
    dimension: str,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    raw = raw_pairwise_agreement(choices)
    alpha = krippendorff_alpha_nominal(choices)
    all_choices = [choice for unit in choices.values() for choice in unit]
    tie_rate = sum(choice == CHOICE_TIE for choice in all_choices) / len(all_choices)
    diagnostics = {
        "raw_pairwise_agreement": raw,
        "krippendorff_alpha_nominal": alpha,
        "tie_rate": tie_rate,
        "gating": False,
    }

    aggregate: dict[str, Any] = {}
    per_brief: dict[str, Any] = defaultdict(dict)
    for baseline in BASELINES:
        baseline_choices = [
            choice
            for (triplet_id, unit_baseline), unit in choices.items()
            if unit_baseline == baseline
            for choice in unit
        ]
        fraction, counts = preference_fraction(baseline_choices)
        aggregate[baseline] = {"preference": fraction, "counts": counts}
        for brief_id in BRIEF_IDS:
            brief_choices = [
                choice
                for (triplet_id, unit_baseline), unit in choices.items()
                if unit_baseline == baseline and triplet_briefs[triplet_id] == brief_id
                for choice in unit
            ]
            brief_fraction, brief_counts = preference_fraction(brief_choices)
            per_brief[brief_id][baseline] = {
                "preference": brief_fraction,
                "counts": brief_counts,
            }

    thresholds = primary_thresholds(protocol)
    rule = evaluate_dimension_requirement(
        aggregate=aggregate,
        per_brief=per_brief,
        threshold=float(thresholds[dimension]),
        per_brief_preference_floor=float(
            protocol["pass_rule"]["per_brief_preference_floor"]
        ),
        briefs_required=int(thresholds["briefs_required_to_clear_each_primary"]),
    )
    return (
        diagnostics,
        {"aggregate": aggregate, "per_brief": dict(per_brief), "rule": rule},
        bool(rule["requirement_passed"]),
    )


def simulate_primary_trial(
    *,
    rng: random.Random,
    true_preference: float,
    protocol: dict[str, Any],
    assignments: dict[str, list[str]],
    tie_rate: float,
    rater_sd_logit: float,
    brief_sd_logit: float,
    dimension_sd_logit: float,
    run_sd_logit: float,
    continuity_pass_probability: float,
    reliability_mode: str,
    anchor_true_preference: float,
    anchor_rater_sd_logit: float,
    anchor_dimension_sd_logit: float,
) -> tuple[str, dict[str, bool], dict[str, Any], dict[str, Any], dict[str, Any]]:
    triplet_ids = sorted(assignments)
    if len(triplet_ids) != 9:
        raise ValueError("The primary simulation requires exactly nine triplets")
    triplet_briefs = {
        triplet_id: BRIEF_IDS[index // 3]
        for index, triplet_id in enumerate(triplet_ids)
    }
    unique_raters = sorted({rater for raters in assignments.values() for rater in raters})

    instrument = simulate_anchor_check(
        rng=rng,
        rater_ids=unique_raters,
        protocol=protocol,
        anchor_true_preference=anchor_true_preference,
        anchor_rater_sd_logit=anchor_rater_sd_logit,
        anchor_dimension_sd_logit=anchor_dimension_sd_logit,
        reliability_mode=reliability_mode,
    )

    rater_effect = {
        rater: rng.gauss(0.0, rater_sd_logit) for rater in unique_raters
    }
    brief_effect = {
        brief: rng.gauss(0.0, brief_sd_logit) for brief in BRIEF_IDS
    }
    run_effect = {
        triplet: rng.gauss(0.0, run_sd_logit) for triplet in triplet_ids
    }
    base_logit = logit(true_preference)

    diagnostics_by_dimension: dict[str, Any] = {}
    summaries: dict[str, Any] = {}
    primary_passes: dict[str, bool] = {}

    for dimension in PRIMARY_DIMENSIONS:
        dimension_effect = rng.gauss(0.0, dimension_sd_logit)
        units: dict[tuple[str, str], list[str]] = defaultdict(list)
        for triplet_id in triplet_ids:
            brief_id = triplet_briefs[triplet_id]
            for rater in assignments[triplet_id]:
                latent = (
                    base_logit
                    + dimension_effect
                    + brief_effect[brief_id]
                    + run_effect[triplet_id]
                    + rater_effect[rater]
                )
                probability = logistic(latent)
                for baseline in BASELINES:
                    units[(triplet_id, baseline)].append(
                        draw_choice(rng, probability, tie_rate)
                    )
        diagnostics, summary, passed = summarize_dimension(
            choices=units,
            triplet_briefs=triplet_briefs,
            protocol=protocol,
            dimension=dimension,
        )
        diagnostics_by_dimension[dimension] = diagnostics
        summaries[dimension] = summary
        primary_passes[dimension] = passed

    continuity_non_inferior = rng.random() < continuity_pass_probability
    decision = classify_primary_decision(
        primary_passes=primary_passes,
        instrument_valid=bool(instrument["valid"]),
        continuity_non_inferior=continuity_non_inferior,
    )
    return decision, primary_passes, diagnostics_by_dimension, summaries, instrument


def simulate_repeat_trial(
    *,
    rng: random.Random,
    true_preference: float,
    protocol: dict[str, Any],
    affected_dimensions: set[str],
    previously_passing_dimensions: set[str],
    tie_rate: float,
    rater_sd_logit: float,
    brief_sd_logit: float,
    dimension_sd_logit: float,
    run_sd_logit: float,
    continuity_pass_probability: float,
) -> bool:
    repeat_runs = int(protocol["mixed_repeat"]["runs_per_condition"])
    triplet_ids = tuple(f"reserve_{index}" for index in range(1, repeat_runs + 1))
    rater_ids = ("reserve_rater_1", "reserve_rater_2", "reserve_rater_3")
    base_logit = logit(true_preference)
    brief_effect = rng.gauss(0.0, brief_sd_logit)
    rater_effect = {
        rater: rng.gauss(0.0, rater_sd_logit) for rater in rater_ids
    }
    run_effect = {
        triplet: rng.gauss(0.0, run_sd_logit) for triplet in triplet_ids
    }

    aggregate_by_dimension: dict[str, Any] = {}
    for dimension in PRIMARY_DIMENSIONS:
        dimension_effect = rng.gauss(0.0, dimension_sd_logit)
        units: dict[tuple[str, str], list[str]] = defaultdict(list)
        for triplet_id in triplet_ids:
            for rater in rater_ids:
                probability = logistic(
                    base_logit
                    + dimension_effect
                    + brief_effect
                    + run_effect[triplet_id]
                    + rater_effect[rater]
                )
                for baseline in BASELINES:
                    units[(triplet_id, baseline)].append(
                        draw_choice(rng, probability, tie_rate)
                    )
        aggregate: dict[str, Any] = {}
        for baseline in BASELINES:
            values = [
                choice
                for (_triplet_id, unit_baseline), unit in units.items()
                if unit_baseline == baseline
                for choice in unit
            ]
            fraction, counts = preference_fraction(values)
            aggregate[baseline] = {"preference": fraction, "counts": counts}
        aggregate_by_dimension[dimension] = aggregate

    result = evaluate_mixed_repeat(
        aggregate_by_dimension=aggregate_by_dimension,
        affected_dimensions=affected_dimensions,
        previously_passing_dimensions=previously_passing_dimensions,
        protocol=protocol,
        continuity_non_inferior=rng.random() < continuity_pass_probability,
        instrument_valid=True,  # inherited from primary when the same instrument/pool is used
    )
    return bool(result["passed"])


def simulate_point(
    *,
    seed: int,
    trials: int,
    true_preference: float,
    protocol: dict[str, Any],
    assignments: dict[str, list[str]],
    tie_rate: float,
    rater_sd_logit: float,
    brief_sd_logit: float,
    dimension_sd_logit: float,
    run_sd_logit: float,
    continuity_pass_probability: float,
    reliability_mode: str,
    anchor_true_preference: float,
    anchor_rater_sd_logit: float,
    anchor_dimension_sd_logit: float,
) -> dict[str, Any]:
    rng = random.Random(seed)
    primary_counts: Counter[str] = Counter()
    mixed_trials = 0
    mixed_passes = 0
    instrument_passes = 0
    diagnostic_values: dict[str, dict[str, list[float]]] = {
        dimension: {
            "raw_pairwise_agreement": [],
            "krippendorff_alpha_nominal": [],
            "tie_rate": [],
        }
        for dimension in PRIMARY_DIMENSIONS
    }

    for _ in range(trials):
        decision, primary_passes, diagnostics, _summaries, instrument = (
            simulate_primary_trial(
                rng=rng,
                true_preference=true_preference,
                protocol=protocol,
                assignments=assignments,
                tie_rate=tie_rate,
                rater_sd_logit=rater_sd_logit,
                brief_sd_logit=brief_sd_logit,
                dimension_sd_logit=dimension_sd_logit,
                run_sd_logit=run_sd_logit,
                continuity_pass_probability=continuity_pass_probability,
                reliability_mode=reliability_mode,
                anchor_true_preference=anchor_true_preference,
                anchor_rater_sd_logit=anchor_rater_sd_logit,
                anchor_dimension_sd_logit=anchor_dimension_sd_logit,
            )
        )
        primary_counts[decision] += 1
        instrument_passes += int(bool(instrument["valid"]))
        for dimension, values in diagnostics.items():
            for metric in diagnostic_values[dimension]:
                value = values.get(metric)
                if value is not None and math.isfinite(float(value)):
                    diagnostic_values[dimension][metric].append(float(value))

        if decision == "MIXED":
            mixed_trials += 1
            affected = {
                dimension for dimension, passed in primary_passes.items() if not passed
            }
            previously_passing = {
                dimension for dimension, passed in primary_passes.items() if passed
            }
            if simulate_repeat_trial(
                rng=rng,
                true_preference=true_preference,
                protocol=protocol,
                affected_dimensions=affected,
                previously_passing_dimensions=previously_passing,
                tie_rate=tie_rate,
                rater_sd_logit=rater_sd_logit,
                brief_sd_logit=brief_sd_logit,
                dimension_sd_logit=dimension_sd_logit,
                run_sd_logit=run_sd_logit,
                continuity_pass_probability=continuity_pass_probability,
            ):
                mixed_passes += 1

    primary_probabilities = {
        decision: primary_counts[decision] / trials
        for decision in ("PASS", "MIXED", "FAIL", "INCONCLUSIVE")
    }
    repeat_probability = mixed_passes / mixed_trials if mixed_trials else None
    eventual_pass = primary_probabilities["PASS"] + mixed_passes / trials
    diagnostics_summary = {
        dimension: {
            metric: rounded(fmean(values)) if values else None
            for metric, values in metrics.items()
        }
        for dimension, metrics in diagnostic_values.items()
    }
    return {
        "true_preference": true_preference,
        "primary_decision_probabilities": {
            key: rounded(value) for key, value in primary_probabilities.items()
        },
        "instrument_pass_probability": rounded(instrument_passes / trials),
        "reliability_diagnostic_means": diagnostics_summary,
        "mixed_repeat_runs_per_condition": int(
            protocol["mixed_repeat"]["runs_per_condition"]
        ),
        "mixed_repeat_conditional_trials": mixed_trials,
        "mixed_repeat_conditional_pass_probability": rounded(repeat_probability),
        "eventual_pass_probability": rounded(eventual_pass),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--assignment-plan", type=Path, required=True)
    parser.add_argument(
        "--run-mode",
        choices=("standard_seven", "standard_six", "standard_five", "degraded_three"),
        default="standard_six",
    )
    parser.add_argument("--trials", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=23017)
    parser.add_argument(
        "--true-preferences",
        type=float,
        nargs="+",
        default=(0.55, 0.65, 0.75),
    )
    parser.add_argument("--tie-rate", type=float, default=0.15)
    parser.add_argument("--rater-sd-logit", type=float, default=0.30)
    parser.add_argument("--brief-sd-logit", type=float, default=0.35)
    parser.add_argument("--dimension-sd-logit", type=float, default=0.15)
    parser.add_argument("--run-sd-logit", type=float, default=0.15)
    parser.add_argument("--continuity-pass-probability", type=float, default=1.0)
    parser.add_argument("--anchor-true-preference", type=float, default=0.90)
    parser.add_argument("--anchor-rater-sd-logit", type=float, default=0.30)
    parser.add_argument("--anchor-dimension-sd-logit", type=float, default=0.10)
    parser.add_argument(
        "--reliability-mode",
        choices=("simulate", "assume_interpretable"),
        default="simulate",
        help=(
            "simulate is mandatory for a real freeze and exercises anchor-driven "
            "INCONCLUSIVE risk. assume_interpretable is a non-freezing diagnostic "
            "that isolates the preference rule."
        ),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--review-status",
        choices=("example", "unreviewed", "reviewed"),
        default="unreviewed",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.trials < 1:
        raise SystemExit("--trials must be positive")
    for name, value in (("tie-rate", args.tie_rate),):
        if not 0 <= value < 1:
            raise SystemExit(f"--{name} must be in [0, 1)")
    for name, value in (
        ("anchor-true-preference", args.anchor_true_preference),
        *[("true-preference", value) for value in args.true_preferences],
    ):
        if not 0 < value < 1:
            raise SystemExit(f"--{name} must be in (0, 1)")

    protocol = load_yaml(args.protocol)
    plan = load_yaml(args.assignment_plan)
    plan_key, assignments = assignment_for_mode(plan, args.run_mode)

    central = {
        "name": "calibration_central",
        "tie_rate": args.tie_rate,
        "rater_sd_logit": args.rater_sd_logit,
        "brief_sd_logit": args.brief_sd_logit,
        "anchor_true_preference": args.anchor_true_preference,
        "anchor_rater_sd_logit": args.anchor_rater_sd_logit,
    }
    scenarios = [
        central,
        {
            "name": "lower_heterogeneity",
            "tie_rate": max(0.0, args.tie_rate - 0.05),
            "rater_sd_logit": args.rater_sd_logit * 0.6,
            "brief_sd_logit": args.brief_sd_logit * 0.6,
            "anchor_true_preference": min(0.99, args.anchor_true_preference + 0.03),
            "anchor_rater_sd_logit": args.anchor_rater_sd_logit * 0.6,
        },
        {
            "name": "higher_heterogeneity",
            "tie_rate": min(0.45, args.tie_rate + 0.10),
            "rater_sd_logit": args.rater_sd_logit * 1.5,
            "brief_sd_logit": args.brief_sd_logit * 1.5,
            "anchor_true_preference": max(0.60, args.anchor_true_preference - 0.08),
            "anchor_rater_sd_logit": args.anchor_rater_sd_logit * 1.5,
        },
    ]

    rendered_scenarios = []
    for scenario_index, scenario in enumerate(scenarios):
        points = []
        for point_index, true_preference in enumerate(args.true_preferences):
            points.append(
                simulate_point(
                    seed=args.seed + scenario_index * 100_000 + point_index * 10_000,
                    trials=args.trials,
                    true_preference=true_preference,
                    protocol=protocol,
                    assignments=assignments,
                    tie_rate=float(scenario["tie_rate"]),
                    rater_sd_logit=float(scenario["rater_sd_logit"]),
                    brief_sd_logit=float(scenario["brief_sd_logit"]),
                    dimension_sd_logit=args.dimension_sd_logit,
                    run_sd_logit=args.run_sd_logit,
                    continuity_pass_probability=args.continuity_pass_probability,
                    reliability_mode=args.reliability_mode,
                    anchor_true_preference=float(scenario["anchor_true_preference"]),
                    anchor_rater_sd_logit=float(scenario["anchor_rater_sd_logit"]),
                    anchor_dimension_sd_logit=args.anchor_dimension_sd_logit,
                )
            )
        rendered_scenarios.append({**scenario, "points": points})

    rule_path = Path(__file__).with_name("m4_rules.py")
    output = {
        "simulation_version": "2.4.0",
        "protocol_hash": "sha256:" + hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
        "rule_source_hash": "sha256:" + hashlib.sha256(rule_path.read_bytes()).hexdigest(),
        "seed": args.seed,
        "trials_per_point": args.trials,
        "run_mode": args.run_mode,
        "assumptions": {
            "assignment_plan": plan_key,
            "tie_rate": args.tie_rate,
            "rater_sd_logit": args.rater_sd_logit,
            "brief_sd_logit": args.brief_sd_logit,
            "dimension_sd_logit": args.dimension_sd_logit,
            "run_sd_logit": args.run_sd_logit,
            "continuity_pass_probability": args.continuity_pass_probability,
            "reliability_mode": args.reliability_mode,
            "anchor_true_preference": args.anchor_true_preference,
            "anchor_rater_sd_logit": args.anchor_rater_sd_logit,
            "anchor_dimension_sd_logit": args.anchor_dimension_sd_logit,
            "mixed_repeat_runs_per_condition": int(
                protocol["mixed_repeat"]["runs_per_condition"]
            ),
        },
        "scenarios": rendered_scenarios,
        "review": {
            "status": args.review_status,
            "reviewed_by": None,
            "reviewed_at": None,
            "rationale": (
                "Illustrative package fixture only; replace assumptions with calibration-observed "
                "values, keep reliability_mode=simulate, and record a human review before freeze."
                if args.review_status == "example"
                else None
            ),
        },
    }

    text = json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
