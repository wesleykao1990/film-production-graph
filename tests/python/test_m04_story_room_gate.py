from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from film_graph.application import (
    AnchorTaskRecord,
    GateSampleRecord,
    build_rater_projection,
    build_run_manifest,
)
from film_graph.domain import StoryRoomFinding, StoryRoomValidationReport
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
HASH = "sha256:" + ("a" * 64)


def report(*codes: str) -> StoryRoomValidationReport:
    return StoryRoomValidationReport.from_findings(
        StoryRoomFinding(code, code, code) for code in codes
    )


def anchor_tasks() -> tuple[AnchorTaskRecord, AnchorTaskRecord]:
    return (
        AnchorTaskRecord(
            anchor_id="anchor-specificity-voice",
            dimensions=("specificity", "character_voice"),
            left_sample_id="anchor-intact",
            right_sample_id="anchor-degraded-sv",
            intact_sample_id="anchor-intact",
            degraded_sample_id="anchor-degraded-sv",
        ),
        AnchorTaskRecord(
            anchor_id="anchor-causality",
            dimensions=("causal_progression",),
            left_sample_id="anchor-intact",
            right_sample_id="anchor-degraded-causal",
            intact_sample_id="anchor-intact",
            degraded_sample_id="anchor-degraded-causal",
        ),
    )


def opaque_triplet_ids() -> dict[str, str]:
    return {
        f"triplet-{brief_index}-{run_index}": (f"masked-group-{(brief_index - 1) * 3 + run_index}")
        for brief_index in (1, 2, 3)
        for run_index in (1, 2, 3)
    }


def samples() -> list[GateSampleRecord]:
    values: list[GateSampleRecord] = []
    conditions = ("equal_information", "fixed_budget_conventional", "story_room")
    for brief_index, brief in enumerate(("brief-a", "brief-b", "brief-c"), start=1):
        for run_index in (1, 2, 3):
            for condition_index, condition in enumerate(conditions):
                sample_id = f"{brief}-r{run_index}-{condition_index}"
                values.append(
                    GateSampleRecord(
                        sample_id=sample_id,
                        triplet_id=f"triplet-{brief_index}-{run_index}",
                        brief_id=brief,
                        run_index=run_index,
                        condition=condition,
                        valid=True,
                        target_scene_position=2,
                        target_scene_id=f"{sample_id}-scene",
                        target_scene_hash=HASH,
                        validation_report=report(),
                        cost_usd=0.25 + condition_index,
                        latency_seconds=2 + run_index,
                    )
                )
    return values


def manifest() -> dict[str, Any]:
    return build_run_manifest(
        reversed(samples()),
        anchor_tasks(),
        protocol_hash=HASH,
        anchor_manifest_hash=HASH,
        run_mode="standard_six",
    )


def test_manifest_is_schema_valid_and_order_is_deterministic() -> None:
    first = manifest()
    second = build_run_manifest(
        list(reversed(samples())),
        list(reversed(anchor_tasks())),
        protocol_hash=HASH,
        anchor_manifest_hash=HASH,
        run_mode="standard_six",
    )
    assert first == second
    schema = json.loads((ROOT / "schemas/m4-run-manifest.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(first))
    assert not errors
    assert len(first["triplets"]) == 9


def test_gate_samples_require_concrete_report_and_consistent_validity() -> None:
    original = samples()[0]
    with pytest.raises(ValueError, match="StoryRoomValidationReport"):
        replace(original, validation_report=cast(Any, {"valid": True, "findings": []}))
    with pytest.raises(ValueError, match="valid samples require"):
        replace(original, validation_report=report("hard_error"))

    warning_report = StoryRoomValidationReport.from_findings(
        (StoryRoomFinding("note", "note", "diagnostic", severity="warning"),)
    )
    warning_sample = replace(original, validation_report=warning_report)
    assert warning_sample.validation_report.valid is True
    with pytest.raises(ValueError, match="severity"):
        StoryRoomFinding("bad", "bad", "bad", severity=cast(Any, "critical"))


def test_invalid_external_failure_keeps_concrete_report_and_reason() -> None:
    original = samples()[0]
    invalid = replace(
        original,
        valid=False,
        invalid_reason="external provider failure",
        validation_report=report("external_failure"),
    )
    assert invalid.validation_report.valid is False
    assert invalid.invalid_reason == "external provider failure"


def test_hard_violation_count_is_derived_and_valid_errors_are_rejected() -> None:
    changed = samples()
    with pytest.raises(ValueError, match="valid samples require"):
        build_run_manifest(
            [replace(changed[0], validation_report=report("hard_error")), *changed[1:]],
            anchor_tasks(),
            protocol_hash=HASH,
            anchor_manifest_hash=HASH,
            run_mode="standard_six",
        )


def test_invalid_sample_requires_reason_and_preserves_derived_count() -> None:
    changed = samples()
    original = changed[0]
    changed[0] = GateSampleRecord(
        sample_id=original.sample_id,
        triplet_id=original.triplet_id,
        brief_id=original.brief_id,
        run_index=original.run_index,
        condition=original.condition,
        valid=False,
        invalid_reason="schema failure",
        validation_report=report("missing_scene", "bad_hash"),
        cost_usd=original.cost_usd,
        latency_seconds=original.latency_seconds,
    )
    built = build_run_manifest(
        changed,
        anchor_tasks(),
        protocol_hash=HASH,
        anchor_manifest_hash=HASH,
        run_mode="standard_six",
    )
    row = built["triplets"][0]["samples"][0]
    assert row["valid"] is False
    assert row["hard_violation_count"] == 2
    assert row["invalid_reason"] == "schema failure"


def test_projection_is_opaque_and_requires_exact_pre_frozen_assignments() -> None:
    built = manifest()
    all_sample_ids = {
        sample["sample_id"] for triplet in built["triplets"] for sample in triplet["samples"]
    }
    all_sample_ids.update({"anchor-intact", "anchor-degraded-sv", "anchor-degraded-causal"})
    assignments = {
        sample_id: {"label": f"opaque-{index}", "content_token": f"content-{index}"}
        for index, sample_id in enumerate(sorted(all_sample_ids))
    }
    projected = build_rater_projection(
        built,
        assignments,
        opaque_task_ids={
            "anchor-specificity-voice": "task-1",
            "anchor-causality": "task-2",
        },
        opaque_triplet_ids=opaque_triplet_ids(),
    )
    encoded = json.dumps(projected)
    assert "condition" not in encoded
    assert "brief_id" not in encoded
    assert "run_index" not in encoded
    assert "intact_sample_id" not in encoded
    assert "degraded_sample_id" not in encoded
    assert "anchor_id" not in encoded
    assert "content_ref" not in encoded
    assert "brief-a" not in encoded
    assert "brief-b" not in encoded
    assert "brief-c" not in encoded
    assert "triplet-" not in encoded
    for source_id in all_sample_ids | set(opaque_triplet_ids()):
        assert source_id not in encoded
    assert "story_room" not in encoded
    assert "equal_information" not in encoded
    assert "fixed_budget_conventional" not in encoded
    assert len(projected["triplets"]) == 9
    with pytest.raises(ValueError, match="coverage mismatch"):
        build_rater_projection(
            built,
            {key: value for key, value in assignments.items() if key != "anchor-intact"},
            opaque_task_ids={
                "anchor-specificity-voice": "task-1",
                "anchor-causality": "task-2",
            },
            opaque_triplet_ids=opaque_triplet_ids(),
        )

    with pytest.raises(ValueError, match="opaque_triplet_ids are required"):
        build_rater_projection(
            built,
            assignments,
            opaque_task_ids={
                "anchor-specificity-voice": "task-1",
                "anchor-causality": "task-2",
            },
        )


def test_projection_rejects_admin_id_substrings_in_opaque_values() -> None:
    built = manifest()
    all_sample_ids = {
        sample["sample_id"] for triplet in built["triplets"] for sample in triplet["samples"]
    }
    all_sample_ids.update({"anchor-intact", "anchor-degraded-sv", "anchor-degraded-causal"})
    assignments = {
        sample_id: {"label": f"opaque-{index}", "content_token": f"content-{index}"}
        for index, sample_id in enumerate(sorted(all_sample_ids))
    }
    triplets = {
        f"triplet-{brief_index}-{run_index}": f"masked-group-{(brief_index - 1) * 3 + run_index}"
        for brief_index in (1, 2, 3)
        for run_index in (1, 2, 3)
    }
    triplets["triplet-1-1"] = "masked-triplet-1-1"
    with pytest.raises(ValueError, match="admin identifier"):
        build_rater_projection(
            built,
            assignments,
            opaque_task_ids={
                "anchor-specificity-voice": "task-1",
                "anchor-causality": "task-2",
            },
            opaque_triplet_ids=triplets,
        )


def test_projection_rejects_brief_id_substrings_in_content_tokens() -> None:
    built = manifest()
    all_sample_ids = {
        sample["sample_id"] for triplet in built["triplets"] for sample in triplet["samples"]
    }
    all_sample_ids.update({"anchor-intact", "anchor-degraded-sv", "anchor-degraded-causal"})
    assignments = {
        sample_id: {"label": f"opaque-{index}", "content_token": f"content-{index}"}
        for index, sample_id in enumerate(sorted(all_sample_ids))
    }
    assignments[sorted(all_sample_ids)[0]] = {
        "label": "opaque-safe",
        "content_token": "secret-brief-a",
    }
    with pytest.raises(ValueError, match="admin identifier"):
        build_rater_projection(
            built,
            assignments,
            opaque_task_ids={
                "anchor-specificity-voice": "task-1",
                "anchor-causality": "task-2",
            },
            opaque_triplet_ids=opaque_triplet_ids(),
        )


def test_projection_carries_brief_ids_from_sample_records() -> None:
    records = samples()
    all_sample_ids = {item.sample_id for item in records}
    all_sample_ids.update({"anchor-intact", "anchor-degraded-sv", "anchor-degraded-causal"})
    assignments = {
        sample_id: {"label": f"opaque-{index}", "content_token": f"content-{index}"}
        for index, sample_id in enumerate(sorted(all_sample_ids))
    }
    assignments[sorted(all_sample_ids)[0]] = {
        "label": "opaque-safe",
        "content_token": "secret-brief-a",
    }
    with pytest.raises(ValueError, match="admin identifier"):
        build_rater_projection(
            records,
            assignments,
            anchor_tasks=anchor_tasks(),
            opaque_task_ids={
                "anchor-specificity-voice": "task-1",
                "anchor-causality": "task-2",
            },
            opaque_triplet_ids=opaque_triplet_ids(),
        )


def test_projection_requires_content_token_and_rejects_content_aliases() -> None:
    built = manifest()
    all_sample_ids = {
        sample["sample_id"] for triplet in built["triplets"] for sample in triplet["samples"]
    }
    all_sample_ids.update({"anchor-intact", "anchor-degraded-sv", "anchor-degraded-causal"})
    assignments = {
        sample_id: {"label": f"opaque-{index}", "content_token": f"content-{index}"}
        for index, sample_id in enumerate(sorted(all_sample_ids))
    }
    first = sorted(all_sample_ids)[0]
    assignments[first] = {"label": "opaque-first", "content_ref": "legacy-ref"}
    with pytest.raises(ValueError, match="content_token|unsupported fields"):
        build_rater_projection(
            built,
            assignments,
            opaque_task_ids={
                "anchor-specificity-voice": "task-1",
                "anchor-causality": "task-2",
            },
            opaque_triplet_ids=opaque_triplet_ids(),
        )


def test_projection_requires_unique_content_tokens() -> None:
    built = manifest()
    all_sample_ids = {
        sample["sample_id"] for triplet in built["triplets"] for sample in triplet["samples"]
    }
    all_sample_ids.update({"anchor-intact", "anchor-degraded-sv", "anchor-degraded-causal"})
    ordered_ids = sorted(all_sample_ids)
    assignments = {
        sample_id: {"label": f"opaque-{index}", "content_token": f"content-{index}"}
        for index, sample_id in enumerate(ordered_ids)
    }
    assignments[ordered_ids[1]]["content_token"] = assignments[ordered_ids[0]]["content_token"]
    with pytest.raises(ValueError, match="content tokens must be unique"):
        build_rater_projection(
            built,
            assignments,
            opaque_task_ids={
                "anchor-specificity-voice": "task-1",
                "anchor-causality": "task-2",
            },
            opaque_triplet_ids=opaque_triplet_ids(),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "wrong-condition",
        "wrong-position",
        "negative-cost",
    ],
)
def test_complete_sample_matrix_is_required(mutation: str) -> None:
    values = samples()
    if mutation == "missing":
        values.pop()
    elif mutation == "duplicate":
        values[-1] = values[-2]
    elif mutation == "wrong-condition":
        original = values[0]
        values[0] = GateSampleRecord(
            sample_id=original.sample_id,
            triplet_id=original.triplet_id,
            brief_id=original.brief_id,
            run_index=original.run_index,
            condition="story_room",
            valid=original.valid,
            validation_report=original.validation_report,
            target_scene_position=2,
            target_scene_id=original.target_scene_id,
            target_scene_hash=original.target_scene_hash,
        )
    elif mutation == "wrong-position":
        original = values[0]
        values[0] = GateSampleRecord(
            sample_id=original.sample_id,
            triplet_id=original.triplet_id,
            brief_id=original.brief_id,
            run_index=original.run_index,
            condition=original.condition,
            valid=True,
            validation_report=original.validation_report,
            target_scene_position=1,
            target_scene_id=original.target_scene_id,
            target_scene_hash=original.target_scene_hash,
        )
    else:
        original = values[0]
        with pytest.raises(ValueError, match="cost_usd"):
            GateSampleRecord(
                sample_id=original.sample_id,
                triplet_id=original.triplet_id,
                brief_id=original.brief_id,
                run_index=original.run_index,
                condition=original.condition,
                valid=True,
                validation_report=original.validation_report,
                target_scene_position=2,
                target_scene_id=original.target_scene_id,
                target_scene_hash=original.target_scene_hash,
                cost_usd=-1,
            )
        return
    with pytest.raises(ValueError):
        build_run_manifest(
            values,
            anchor_tasks(),
            protocol_hash=HASH,
            anchor_manifest_hash=HASH,
            run_mode="standard_six",
        )
