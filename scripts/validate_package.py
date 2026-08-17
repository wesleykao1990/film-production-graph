#!/usr/bin/env python3
"""Mechanically validate the AI Film Production Graph handoff package."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
TRANSIENT_NAMES = {".DS_Store"}
TRANSIENT_SUFFIXES = (".swp", ".swo", "~")
TRANSIENT_DIR_NAMES = {
    ".branches",
    ".data",
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".temp",
    ".venv",
    "__pycache__",
    "node_modules",
}
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


class ValidationFailure(RuntimeError):
    pass


def is_transient_path(path: Path) -> bool:
    """Return whether a generated dependency/cache path is outside package source."""

    parts = path.relative_to(ROOT).parts
    return (
        any(part in TRANSIENT_DIR_NAMES or part.endswith(".egg-info") for part in parts)
        or path.suffix == ".tsbuildinfo"
    )


def load_data(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def parse_all_data_files() -> tuple[int, list[str]]:
    count = 0
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if (
            is_transient_path(path)
            or not path.is_file()
            or path.suffix.lower() not in {".json", ".yaml", ".yml"}
        ):
            continue
        count += 1
        try:
            load_data(path)
        except Exception as exc:  # noqa: BLE001 - aggregate validation failures
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return count, errors


def schema_registry() -> tuple[dict[Path, dict[str, Any]], Registry]:
    schemas: dict[Path, dict[str, Any]] = {}
    registry = Registry()
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = load_data(path)
        Draft202012Validator.check_schema(schema)
        schemas[path] = schema
        schema_id = schema.get("$id")
        if schema_id:
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    # The rating form is itself a schema stored beside the experiment examples.
    rating_schema_path = ROOT / "examples/evals/story-room-gate/rating_form.schema.json"
    rating_schema = load_data(rating_schema_path)
    Draft202012Validator.check_schema(rating_schema)
    schemas[rating_schema_path] = rating_schema
    if rating_schema.get("$id"):
        registry = registry.with_resource(
            rating_schema["$id"], Resource.from_contents(rating_schema)
        )
    return schemas, registry


def validate_instance(
    instance_path: Path,
    schema_path: Path,
    *,
    schemas: dict[Path, dict[str, Any]],
    registry: Registry,
) -> list[str]:
    instance = load_data(instance_path)
    schema = schemas.get(schema_path) or load_data(schema_path)
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(
            f"{instance_path.relative_to(ROOT)} @ {where} against "
            f"{schema_path.relative_to(ROOT)}: {error.message}"
        )
    return errors


def validate_mapped_instances(
    schemas: dict[Path, dict[str, Any]], registry: Registry
) -> tuple[int, list[str]]:
    errors: list[str] = []
    count = 0
    fixture_dir = ROOT / "examples/golden/blue-pen-fixture"
    fixture_manifest = load_data(fixture_dir / "fixture-manifest.yaml")
    for mapping in fixture_manifest["validation"]["schema_instances"]:
        instance_path = fixture_dir / mapping["file"]
        schema_path = ROOT / mapping["schema"]
        if not instance_path.exists():
            errors.append(f"Missing mapped fixture: {instance_path.relative_to(ROOT)}")
            continue
        if not schema_path.exists():
            errors.append(f"Missing mapped schema: {schema_path.relative_to(ROOT)}")
            continue
        count += 1
        errors.extend(
            validate_instance(instance_path, schema_path, schemas=schemas, registry=registry)
        )

    explicit = [
        (
            ROOT / "examples/skills/subtext-pass/skill.yaml",
            ROOT / "schemas/skill-manifest.schema.json",
        ),
        (
            ROOT / "examples/skills/skills.lock.example.yaml",
            ROOT / "schemas/skills-lock.schema.json",
        ),
        (
            ROOT / "examples/workflows/dialogue-development.workflow.yaml",
            ROOT / "schemas/workflow-plan.schema.json",
        ),
        (
            ROOT / "skills/subtext-pass/skill.yaml",
            ROOT / "schemas/skill-manifest.schema.json",
        ),
        (
            ROOT / "skills.lock",
            ROOT / "schemas/skills-lock.schema.json",
        ),
        (
            ROOT / "workflows/dialogue-development.workflow.yaml",
            ROOT / "schemas/workflow-plan.schema.json",
        ),
        (
            ROOT / "workflows/prototype-subtext-review.workflow.yaml",
            ROOT / "schemas/workflow-plan.schema.json",
        ),
        (
            ROOT / "examples/evals/story-room-gate/protocol.yaml",
            ROOT / "schemas/m4-experiment-protocol.schema.json",
        ),
        (
            ROOT / "examples/evals/story-room-gate/anchors/anchor-manifest.example.yaml",
            ROOT / "schemas/m4-anchor-manifest.schema.json",
        ),
        (
            ROOT / "examples/evals/story-room-gate/run-manifest.example.yaml",
            ROOT / "schemas/m4-run-manifest.schema.json",
        ),
        (
            ROOT / "examples/evals/story-room-gate/analysis-output.example.json",
            ROOT / "schemas/m4-analysis-report.schema.json",
        ),
        (
            ROOT / "examples/evals/story-room-gate/analysis/operating-characteristics.example.json",
            ROOT / "schemas/m4-operating-characteristics.schema.json",
        ),
    ]
    for instance_path, schema_path in explicit:
        count += 1
        errors.extend(
            validate_instance(instance_path, schema_path, schemas=schemas, registry=registry)
        )

    rating_schema = ROOT / "examples/evals/story-room-gate/rating_form.schema.json"
    ratings_path = ROOT / "examples/evals/story-room-gate/ratings.example.jsonl"
    parsed_ratings: list[dict[str, Any]] = []
    validator = Draft202012Validator(
        schemas[rating_schema], registry=registry, format_checker=FormatChecker()
    )
    for line_number, raw in enumerate(ratings_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        count += 1
        temp = json.loads(raw)
        parsed_ratings.append(temp)
        for error in validator.iter_errors(temp):
            where = "/".join(str(part) for part in error.absolute_path) or "<root>"
            errors.append(f"{ratings_path.relative_to(ROOT)}:{line_number} @ {where}: {error.message}")

    # Contract distinction: scored comparisons may use tie, but positive-control
    # anchors are forced choice. Validate both directions mechanically so a later
    # schema edit cannot silently reintroduce the anchor-coverage ceiling.
    anchor_record = next(
        (item for item in parsed_ratings if item.get("record_type") == "anchor"), None
    )
    if anchor_record is None:
        errors.append("Rating fixture lacks an anchor record for forced-choice validation")
    else:
        count += 1
        invalid_anchor = copy.deepcopy(anchor_record)
        invalid_anchor["anchor_ratings"][0]["choice"] = "tie"
        if not list(validator.iter_errors(invalid_anchor)):
            errors.append("Rating schema incorrectly accepts an anchor tie")

    triplet_record = next(
        (item for item in parsed_ratings if item.get("record_type") == "triplet"), None
    )
    if triplet_record is None:
        errors.append("Rating fixture lacks a scored triplet for tie validation")
    else:
        count += 1
        scored_tie = copy.deepcopy(triplet_record)
        scored_tie["primary_ratings"][0]["choice"] = "tie"
        scored_errors = list(validator.iter_errors(scored_tie))
        if scored_errors:
            errors.append("Rating schema incorrectly rejects a scored-item tie")
    return count, errors


def should_ignore_skill_path(path: Path) -> bool:
    return (
        path.name in TRANSIENT_NAMES
        or "__pycache__" in path.parts
        or path.name.endswith(TRANSIENT_SUFFIXES)
    )


def skill_hash(skill_root: Path, overrides: dict[str, bytes] | None = None) -> str:
    overrides = overrides or {}
    files: list[Path] = []
    for path in skill_root.rglob("*"):
        if path.is_symlink():
            raise ValidationFailure(f"Skill contains symlink: {path.relative_to(ROOT)}")
        if path.is_file() and not should_ignore_skill_path(path):
            if os.access(path, os.X_OK):
                raise ValidationFailure(f"Skill contains executable file: {path.relative_to(ROOT)}")
            files.append(path)
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda p: p.relative_to(skill_root).as_posix().encode("utf-8")):
        relative = path.relative_to(skill_root).as_posix()
        data = overrides.get(relative, path.read_bytes())
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def validate_skill_lock() -> list[str]:
    errors: list[str] = []
    for lock_path in (
        ROOT / "examples/skills/skills.lock.example.yaml",
        ROOT / "skills.lock",
    ):
        lock = load_data(lock_path)
        entry = lock["skills"]["subtext-pass"]
        skill_root = ROOT / entry["source_path"]
        actual = skill_hash(skill_root)
        if actual != entry["content_hash"]:
            errors.append(
                f"{lock_path.relative_to(ROOT)} mismatch: expected "
                f"{entry['content_hash']}, computed {actual}"
            )
        reference_path = skill_root / "references/method.md"
        modified = reference_path.read_bytes() + b"\nvalidation drift probe\n"
        drifted = skill_hash(skill_root, {"references/method.md": modified})
        if drifted == actual:
            errors.append(
                f"{lock_path.relative_to(ROOT)} did not invalidate after reference drift"
            )
    return errors


def markdown_link_errors() -> tuple[int, list[str]]:
    checked = 0
    errors: list[str] = []
    excluded: set[Path] = set()
    for path in sorted(ROOT.rglob("*.md")):
        if path in excluded or is_transient_path(path):
            continue
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#", "sandbox:", "skills://")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            checked += 1
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)} escapes package root: {raw_target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)} -> missing {raw_target}")
    return checked, errors


def validate_assignment_plan() -> tuple[int, list[str]]:
    errors: list[str] = []
    plan = load_data(ROOT / "examples/evals/story-room-gate/assignment-plan.example.yaml")
    expected_triplets = {f"T{i:02d}" for i in range(1, 10)}
    configs = [
        ("standard_timing_fallback_seven_raters", 3, 4),
        ("standard_target_six_raters", 3, 5),
        ("standard_fallback_five_raters", 3, 6),
        ("degraded_three_rater_mode", 3, 9),
    ]
    checked = 0
    primary_rater_sets: dict[str, set[str]] = {}
    for name, expected_per_triplet, max_per_rater in configs:
        checked += 1
        triplets = plan[name]["triplets"]
        if set(triplets) != expected_triplets:
            errors.append(f"{name} does not cover T01..T09 exactly")
        rater_load: dict[str, int] = {}
        for triplet_id, raters in triplets.items():
            if len(raters) != expected_per_triplet:
                errors.append(
                    f"{name}/{triplet_id} has {len(raters)} raters; expected {expected_per_triplet}"
                )
            if len(set(raters)) != len(raters):
                errors.append(f"{name}/{triplet_id} contains duplicate raters")
            for rater in raters:
                rater_load[rater] = rater_load.get(rater, 0) + 1
        overloaded = {r: n for r, n in rater_load.items() if n > max_per_rater}
        if overloaded:
            errors.append(f"{name} overloads raters: {overloaded}")
        primary_rater_sets[name] = set(rater_load)

    anchors = plan.get("positive_control_anchors", {})
    if set(anchors.get("task_ids", [])) != {
        "ANCHOR-SPECIFICITY-VOICE",
        "ANCHOR-CAUSALITY",
    }:
        errors.append("Positive-control assignment does not include both frozen anchor tasks")
    if anchors.get("assignment_policy") != "every_completed_primary_rater_rates_every_anchor":
        errors.append("Positive-control anchors must be completed by every primary rater")
    checked += 1

    repeat = plan.get("mixed_repeat_assignments", {})
    repeat_runs = int(repeat.get("runs_per_condition", 0))
    ratings_per_triplet = int(repeat.get("ratings_per_triplet", 0))
    expected_repeat_ids = {f"MR{i:02d}" for i in range(1, 6)}
    if repeat_runs != 5:
        errors.append(f"MIXED repeat has {repeat_runs} runs; expected 5")
    if ratings_per_triplet != 3:
        errors.append(f"MIXED repeat has {ratings_per_triplet} ratings per triplet; expected 3")
    repeat_modes = {
        "standard_six": ("standard_target_six_raters", 3),
        "standard_seven": ("standard_timing_fallback_seven_raters", 3),
        "standard_five": ("standard_fallback_five_raters", 3),
        "degraded_three": ("degraded_three_rater_mode", 3),
    }
    for repeat_name, (primary_name, expected_per_triplet) in repeat_modes.items():
        checked += 1
        mapping = repeat.get(repeat_name, {})
        if set(mapping) != expected_repeat_ids:
            errors.append(f"mixed_repeat_assignments/{repeat_name} does not cover MR01..MR05")
        repeat_raters: set[str] = set()
        for triplet_id, raters in mapping.items():
            if len(raters) != expected_per_triplet or len(set(raters)) != len(raters):
                errors.append(
                    f"mixed_repeat_assignments/{repeat_name}/{triplet_id} must have "
                    f"{expected_per_triplet} distinct raters"
                )
            repeat_raters.update(raters)
        if not repeat_raters.issubset(primary_rater_sets[primary_name]):
            errors.append(
                f"mixed_repeat_assignments/{repeat_name} uses raters outside its primary pool"
            )
    return checked, errors


def validate_m4_example() -> list[str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from analyze_m4 import analyze, load_jsonl, load_yaml  # type: ignore

    base = ROOT / "examples/evals/story-room-gate"
    protocol_path = base / "protocol.yaml"
    manifest_path = base / "run-manifest.example.yaml"
    protocol = load_yaml(protocol_path)
    manifest = load_yaml(manifest_path)
    expected_hash = "sha256:" + hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    if manifest.get("protocol_hash") != expected_hash:
        return ["M04 example run manifest protocol_hash does not match protocol.yaml"]
    report = analyze(
        protocol,
        manifest,
        load_jsonl(base / "ratings.example.jsonl"),
    )
    stored = json.loads((base / "analysis-output.example.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    if report != stored:
        errors.append("Stored M04 analysis output does not match scripts/analyze_m4.py")
    if report.get("decision") != "PASS":
        errors.append(f"Executable M04 example expected PASS; got {report.get('decision')}")
    return errors


def validate_operating_characteristics_example() -> list[str]:
    errors: list[str] = []
    base = ROOT / "examples/evals/story-room-gate"
    protocol_path = base / "protocol.yaml"
    rule_path = ROOT / "scripts/m4_rules.py"
    output_path = base / "analysis/operating-characteristics.example.json"
    output = json.loads(output_path.read_text(encoding="utf-8"))

    expected_protocol_hash = "sha256:" + hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    expected_rule_hash = "sha256:" + hashlib.sha256(rule_path.read_bytes()).hexdigest()
    if output.get("protocol_hash") != expected_protocol_hash:
        errors.append("Operating-characteristics example protocol_hash is stale")
    if output.get("rule_source_hash") != expected_rule_hash:
        errors.append("Operating-characteristics example rule_source_hash is stale")

    protocol = load_data(protocol_path)
    assumptions = output.get("assumptions", {})
    if assumptions.get("reliability_mode") != "simulate":
        errors.append(
            "Freeze-eligible operating characteristics must use reliability_mode=simulate"
        )
    expected_repeat_runs = int(protocol["mixed_repeat"]["runs_per_condition"])
    if int(assumptions.get("mixed_repeat_runs_per_condition", 0)) != expected_repeat_runs:
        errors.append("Operating-characteristics repeat run count does not match protocol")

    required = set(
        float(value)
        for value in protocol["operating_characteristics"]["required_true_preferences"]
    )
    central = next(
        (
            scenario
            for scenario in output.get("scenarios", [])
            if scenario.get("name") == "calibration_central"
        ),
        None,
    )
    if central is None:
        errors.append("Operating-characteristics example lacks calibration_central scenario")
    else:
        observed = {float(point["true_preference"]) for point in central.get("points", [])}
        if not required.issubset(observed):
            errors.append(
                "Operating-characteristics example misses required preference points: "
                f"{sorted(required - observed)}"
            )
        inconclusive_values = [
            float(point["primary_decision_probabilities"]["INCONCLUSIVE"])
            for point in central.get("points", [])
        ]
        if not inconclusive_values or not any(0.0 < value < 0.95 for value in inconclusive_values):
            errors.append(
                "Central operating characteristics do not exercise a non-degenerate "
                "INCONCLUSIVE branch"
            )
        if any(
            int(point.get("mixed_repeat_runs_per_condition", 0)) != expected_repeat_runs
            for point in central.get("points", [])
        ):
            errors.append("Operating-characteristics points use the wrong repeat run count")

    scenario_names = {scenario.get("name") for scenario in output.get("scenarios", [])}
    for required_name in {"calibration_central", "lower_heterogeneity", "higher_heterogeneity"}:
        if required_name not in scenario_names:
            errors.append(f"Operating-characteristics example lacks {required_name} scenario")

    if int(output.get("trials_per_point", 0)) < int(
        protocol["operating_characteristics"]["trials_minimum"]
    ):
        errors.append("Operating-characteristics example uses fewer than the protocol minimum trials")
    return errors


def validate_known_paths() -> list[str]:
    errors: list[str] = []
    protocol = load_data(ROOT / "examples/evals/story-room-gate/protocol.yaml")
    base = ROOT / "examples/evals/story-room-gate"
    for condition in protocol["conditions"]:
        path = (base / condition["prompt_path"]).resolve()
        if not path.exists():
            errors.append(f"M04 prompt path does not exist: {condition['prompt_path']}")
    for field in ("calibration_brief", "reserve_brief_commitment"):
        path = base / protocol[field]
        if not path.exists():
            errors.append(f"M04 {field} path does not exist: {protocol[field]}")
    for relative in protocol["primary_briefs"]:
        if not (base / relative).exists():
            errors.append(f"M04 primary brief path does not exist: {relative}")

    anchor_manifest_path = base / protocol["instrument_validity"]["positive_control"]["anchor_manifest"]
    if not anchor_manifest_path.exists():
        errors.append(f"M04 anchor manifest does not exist: {anchor_manifest_path.relative_to(ROOT)}")
    else:
        anchor_manifest = load_data(anchor_manifest_path)
        for sample in anchor_manifest.get("samples", []):
            sample_path = anchor_manifest_path.parent / sample["path"]
            if not sample_path.exists():
                errors.append(f"M04 anchor sample does not exist: {sample_path.relative_to(ROOT)}")
                continue
            actual = "sha256:" + hashlib.sha256(sample_path.read_bytes()).hexdigest()
            if actual != sample["sha256"]:
                errors.append(f"M04 anchor sample hash is stale: {sample_path.relative_to(ROOT)}")
        run_manifest = load_data(base / "run-manifest.example.yaml")
        actual_manifest_hash = "sha256:" + hashlib.sha256(anchor_manifest_path.read_bytes()).hexdigest()
        if run_manifest.get("anchor_manifest_hash") != actual_manifest_hash:
            errors.append("M04 run manifest anchor_manifest_hash is stale")

    old_prompt = ROOT / "prompts/milestones/M04_STORY_ROOM_GATE.md"
    if old_prompt.exists():
        errors.append("Obsolete unsplit M04 prompt is still present")
    for required in (
        ROOT / "PRD.md",
        ROOT / "IMPLEMENTATION_PLAN.md",
        ROOT / "INITIAL_PROMPT.md",
        ROOT / "prototype/README.md",
        ROOT / "prototype/app/main.py",
        ROOT / "prototype/data/seed_project.json",
        ROOT / "skills.lock",
        ROOT / "workflows/prototype-subtext-review.workflow.yaml",
        ROOT / "prompts/milestones/M04A_STORY_ROOM_GATE.md",
        ROOT / "prompts/milestones/M04B_STORY_ROOM_COMPLETION.md",
        ROOT / "templates/DIALOGUE_FEASIBILITY_SPIKE.md",
        ROOT / "scripts/m4_rules.py",
        ROOT / "scripts/simulate_m4.py",
        ROOT / "examples/evals/story-room-gate/anchors/anchor-manifest.example.yaml",
        ROOT / "examples/evals/story-room-gate/analysis/operating-characteristics.example.json",
    ):
        if not required.exists():
            errors.append(f"Missing revised path: {required.relative_to(ROOT)}")
    return errors


def verify_checksums() -> tuple[int, list[str]]:
    checksum_path = ROOT / "CHECKSUMS.sha256"
    errors: list[str] = []
    count = 0
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.exists():
            errors.append(f"Checksum target missing: {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"Checksum mismatch: {relative}")
    expected_paths = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name != "CHECKSUMS.sha256"
        and not is_transient_path(path)
    }
    listed_paths = {
        line.split("  ", 1)[1]
        for line in checksum_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    missing = sorted(expected_paths - listed_paths)
    extra = sorted(listed_paths - expected_paths)
    if missing:
        errors.append(f"Files missing from checksums: {missing}")
    if extra:
        errors.append(f"Extra checksum entries: {extra}")
    return count, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-checksums", action="store_true")
    args = parser.parse_args()

    results: list[tuple[str, int, list[str]]] = []
    parsed, parse_errors = parse_all_data_files()
    results.append(("JSON/YAML parse", parsed, parse_errors))

    try:
        schemas, registry = schema_registry()
        schema_errors: list[str] = []
    except Exception as exc:  # noqa: BLE001
        schemas, registry = {}, Registry()
        schema_errors = [str(exc)]
    results.append(("JSON Schemas", len(schemas), schema_errors))

    if not schema_errors:
        mapped_count, mapped_errors = validate_mapped_instances(schemas, registry)
    else:
        mapped_count, mapped_errors = 0, ["Skipped because schema loading failed"]
    results.append(("Mapped schema instances", mapped_count, mapped_errors))

    results.append(("Skill lock", 1, validate_skill_lock()))
    assignment_count, assignment_errors = validate_assignment_plan()
    results.append(("Assignment plans", assignment_count, assignment_errors))
    results.append(("M04 executable example", 1, validate_m4_example()))
    results.append(("M04 operating characteristics", 1, validate_operating_characteristics_example()))
    results.append(("Known paths", 1, validate_known_paths()))
    link_count, link_errors = markdown_link_errors()
    results.append(("Local Markdown links", link_count, link_errors))
    if args.verify_checksums:
        checksum_count, checksum_errors = verify_checksums()
        results.append(("Checksums", checksum_count, checksum_errors))

    total_errors = 0
    for label, count, errors in results:
        status = "PASS" if not errors else "FAIL"
        print(f"[{status}] {label}: {count}")
        for error in errors:
            print(f"  - {error}")
        total_errors += len(errors)

    if total_errors:
        print(f"Validation failed with {total_errors} error(s).", file=sys.stderr)
        return 1
    print("Package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
