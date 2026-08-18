from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from film_graph.application import (
    ExperimentBudget,
    ExperimentFileRef,
    ExperimentModelIdentity,
    ExperimentPreflightError,
    ProvenanceDestination,
    compile_request_plan,
    preflight_experiment,
)
from film_graph.model_routing import ResolvedModel

CONDITIONS = ("equal_information", "fixed_budget_conventional", "story_room")


def _write(root: Path, relative: str, content: str = "fixture") -> ExperimentFileRef:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ExperimentFileRef.from_file(root, relative)


def _fixture(
    root: Path, *, status: str = "draft"
) -> tuple[dict[str, Any], dict[str, tuple[ExperimentFileRef, ...]]]:
    prompt_refs = tuple(
        _write(root, f"prompts/{condition}.md", f"prompt {condition}")
        for condition in CONDITIONS
    )
    brief_refs = tuple(
        _write(root, f"briefs/{name}.yaml", f"brief {name}")
        for name in ("calibration", "blue", "closed", "genre")
    )
    rules_ref = _write(root, "scripts/m4_rules.py", "rules")
    analyzer_ref = _write(root, "scripts/analyze_m4.py", "analyzer")
    simulator_ref = _write(root, "scripts/simulate_m4.py", "simulator")
    anchor_ref = _write(root, "anchors/manifest.yaml", "anchors")
    assignment_ref = _write(root, "assignment.yaml", "assignments")
    operating_ref = _write(root, "analysis/operating.json", "operating")
    protocol = {
        "status": status,
        "frozen_at": "2026-08-18T00:00:00Z" if status == "frozen" else None,
        "conditions": [
            {"id": condition, "prompt_path": f"prompts/{condition}.md"}
            for condition in CONDITIONS
        ],
        "calibration_brief": "briefs/calibration.yaml",
        "primary_briefs": [
            "briefs/blue.yaml",
            "briefs/closed.yaml",
            "briefs/genre.yaml",
        ],
        "runs_per_condition": 3,
        "presentation": {"assignment_plan": "assignment.yaml"},
        "instrument_validity": {
            "positive_control": {"anchor_manifest": "anchors/manifest.yaml"}
        },
        "budget_freeze": {
            "projected_story_room_cap_usd_per_sample": 1 if status == "frozen" else None,
            "fixed_budget_conventional_multiplier": 1.5,
            "provider_price_snapshot_ref": (
                "price-snapshot-2026-08-18" if status == "frozen" else "REPLACE_BEFORE_FREEZE"
            ),
            "condition_budgets": {
                "equal_information": {
                    "max_model_calls": 2 if status == "frozen" else None,
                    "max_cost_usd": 1 if status == "frozen" else None,
                },
                "fixed_budget_conventional": {
                    "max_model_calls": 2 if status == "frozen" else None,
                    "max_cost_usd": 1.5 if status == "frozen" else None,
                },
                "story_room": {
                    "max_model_calls": 2 if status == "frozen" else None,
                    "max_cost_usd": 1 if status == "frozen" else None,
                },
            },
        },
        "operating_characteristics": {
            "script_path": "scripts/simulate_m4.py",
            "planned_output_path": "analysis/operating.json",
            "trials_minimum": 4000,
            "sensitivity_required": True,
            "mandatory_reliability_mode": "simulate",
            "reviewed_by": "reviewer-ref" if status == "frozen" else None,
            "reviewed_at": "2026-08-18T00:00:00Z" if status == "frozen" else None,
            "output_hash": operating_ref.sha256 if status == "frozen" else None,
            "calibration_inputs": {
                "tie_rate": 0.1 if status == "frozen" else None,
                "rater_sd_logit": 0.3 if status == "frozen" else None,
                "brief_sd_logit": 0.2 if status == "frozen" else None,
                "anchor_true_preference": 0.9 if status == "frozen" else None,
                "anchor_rater_sd_logit": 0.3 if status == "frozen" else None,
            },
        },
    }
    protocol_ref = _write(root, "protocol.yaml", yaml.safe_dump(protocol, sort_keys=False))
    pins: dict[str, tuple[ExperimentFileRef, ...]] = {
        "protocol": (protocol_ref,),
        "prompts": prompt_refs,
        "briefs": brief_refs,
        "rules": (rules_ref,),
        "analyzer": (analyzer_ref,),
        "simulator": (simulator_ref,),
        "anchors": (anchor_ref,),
        "assignments": (assignment_ref,),
        "operating_characteristics": (operating_ref,),
    }
    return protocol, pins


def _model(credential_env: str | None = "MODEL_KEY") -> ExperimentModelIdentity:
    return ExperimentModelIdentity.from_resolved(
        ResolvedModel("story-room-test", "test-provider", "test-model"),
        credential_env=credential_env,
    )


def _repin_protocol(
    root: Path,
    protocol: dict[str, Any],
    pins: dict[str, tuple[ExperimentFileRef, ...]],
) -> dict[str, tuple[ExperimentFileRef, ...]]:
    protocol_ref = _write(root, "protocol.yaml", yaml.safe_dump(protocol, sort_keys=False))
    return {**pins, "protocol": (protocol_ref,)}


def _budgets(*, frozen: bool = False) -> dict[str, ExperimentBudget]:
    budgets = {
        condition: ExperimentBudget(max_model_calls=2, max_cost_usd=Decimal("1.00"))
        for condition in CONDITIONS
    }
    if frozen:
        budgets["fixed_budget_conventional"] = ExperimentBudget(
            max_model_calls=2, max_cost_usd=Decimal("1.50")
        )
    return budgets


def test_dry_run_compiles_three_and_twenty_seven_requests_deterministically(tmp_path: Path) -> None:
    protocol, pins = _fixture(tmp_path)
    calibration = compile_request_plan(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="calibration",
        resolved_model=_model(),
        condition_budgets=_budgets(),
        pinned_refs=pins,
    )
    primary = compile_request_plan(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="primary",
        resolved_model=_model(),
        condition_budgets=_budgets(),
        pinned_refs=pins,
    )
    assert calibration.request_count == 3
    assert primary.request_count == 27
    assert [item.condition for item in calibration.descriptors] == list(CONDITIONS)
    assert [item.run_index for item in primary.descriptors[:3]] == [1, 1, 1]
    assert [item.condition for item in primary.descriptors[:3]] == list(CONDITIONS)
    assert primary.descriptors[3].run_index == 2
    assert primary.as_dict() == replace(primary).as_dict()


def test_dry_run_never_reads_credential_and_execute_reports_missing_key(tmp_path: Path) -> None:
    protocol, pins = _fixture(tmp_path)

    class SecretMapping(Mapping[str, str]):
        def __getitem__(self, key: str) -> str:
            raise AssertionError("dry-run must not inspect the credential mapping")

        def __iter__(self) -> Iterator[str]:
            return iter(())

        def __len__(self) -> int:
            return 0

    dry = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="calibration",
        resolved_model=_model("TOP_SECRET_ENV"),
        condition_budgets=_budgets(),
        pinned_refs=pins,
        mode="dry_run",
        environment=SecretMapping(),
    )
    assert dry.ready
    assert not dry.credential_present

    execute = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="calibration",
        resolved_model=_model("TOP_SECRET_ENV"),
        condition_budgets=_budgets(),
        pinned_refs=pins,
        mode="execute",
        environment={},
        provenance_destination=ProvenanceDestination(str(tmp_path / "provenance.json")),
    )
    assert not execute.ready
    assert any("TOP_SECRET_ENV" in error for error in execute.errors)
    assert "TOP_SECRET_VALUE" not in repr(execute)


def test_stale_hash_zero_budget_and_model_mismatch_are_rejected(tmp_path: Path) -> None:
    protocol, pins = _fixture(tmp_path)
    stale = replace(pins["rules"][0], sha256="sha256:" + "0" * 64)
    bad_pins = {**pins, "rules": (stale,)}
    report = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="calibration",
        resolved_model=_model(),
        condition_budgets=_budgets(),
        pinned_refs=bad_pins,
    )
    assert not report.ready
    assert any("hash mismatch" in error for error in report.errors)

    zero = _budgets()
    zero["story_room"] = ExperimentBudget(max_model_calls=0, max_cost_usd=Decimal("1"))
    with pytest.raises(ExperimentPreflightError, match="positive"):
        compile_request_plan(
            repository_root=tmp_path,
            protocol=protocol,
            protocol_path="protocol.yaml",
            phase="calibration",
            resolved_model=_model(),
            condition_budgets=zero,
            pinned_refs=pins,
        )

    mismatch = _model()
    other = ExperimentModelIdentity("other", mismatch.provider, mismatch.model)
    mismatch_report = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="calibration",
        resolved_model=mismatch,
        condition_budgets=_budgets(),
        pinned_refs=pins,
        condition_models={"story_room": other},
    )
    assert any("model identity mismatch" in error for error in mismatch_report.errors)


def test_primary_execute_rejects_draft_fixture_before_any_provider_boundary(tmp_path: Path) -> None:
    protocol, pins = _fixture(tmp_path, status="draft")
    report = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="primary",
        resolved_model=_model(),
        condition_budgets=_budgets(),
        pinned_refs=pins,
        mode="execute",
        environment={"MODEL_KEY": "TOP_SECRET_VALUE"},
        provenance_destination=ProvenanceDestination(str(tmp_path / "provenance.json")),
    )
    assert not report.ready
    assert any("status frozen" in error for error in report.errors)
    encoded = repr(report) + str(report.as_dict())
    assert "TOP_SECRET_VALUE" not in encoded


def test_primary_execute_accepts_only_matching_frozen_packet_and_redacts_secret(
    tmp_path: Path,
) -> None:
    protocol, pins = _fixture(tmp_path, status="frozen")
    report = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="primary",
        resolved_model=_model(),
        condition_budgets=_budgets(frozen=True),
        pinned_refs=pins,
        mode="execute",
        environment={"MODEL_KEY": "TOP_SECRET_VALUE"},
        provenance_destination=ProvenanceDestination(str(tmp_path / "provenance.json")),
    )
    assert report.ready
    assert report.plan is not None
    assert report.plan.request_count == 27
    assert set(report.plan.pinned_refs) >= {
        "protocol",
        "rules",
        "analyzer",
        "simulator",
        "anchors",
        "assignments",
        "prompts",
        "briefs",
        "operating_characteristics",
    }
    assert "TOP_SECRET_VALUE" not in repr(report)
    assert "TOP_SECRET_VALUE" not in str(report.as_dict())


def test_supplied_protocol_mapping_must_match_pinned_yaml(tmp_path: Path) -> None:
    protocol, pins = _fixture(tmp_path)
    substituted = {**protocol, "runs_per_condition": 99}
    report = preflight_experiment(
        repository_root=tmp_path,
        protocol=substituted,
        protocol_path="protocol.yaml",
        phase="calibration",
        resolved_model=_model(),
        condition_budgets=_budgets(),
        pinned_refs=pins,
    )
    assert not report.ready
    assert any("does not match the pinned protocol" in error for error in report.errors)


def test_protocol_path_must_be_the_pinned_protocol_path(tmp_path: Path) -> None:
    protocol, pins = _fixture(tmp_path)
    report = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="attacker/base/protocol.yaml",
        phase="calibration",
        resolved_model=_model(),
        condition_budgets=_budgets(),
        pinned_refs=pins,
    )
    assert not report.ready
    assert any("protocol_path must match" in error for error in report.errors)


def test_frozen_multiplier_and_materialized_budgets_must_match(tmp_path: Path) -> None:
    protocol, pins = _fixture(tmp_path, status="frozen")
    protocol["budget_freeze"]["fixed_budget_conventional_multiplier"] = 2.0
    protocol["budget_freeze"]["condition_budgets"]["fixed_budget_conventional"][
        "max_cost_usd"
    ] = 2.0
    pins = _repin_protocol(tmp_path, protocol, pins)
    budgets = _budgets(frozen=True)
    budgets["fixed_budget_conventional"] = ExperimentBudget(2, Decimal("2"))
    report = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="primary",
        resolved_model=_model(),
        condition_budgets=budgets,
        pinned_refs=pins,
        mode="execute",
        environment={"MODEL_KEY": "TOP_SECRET_VALUE"},
        provenance_destination=ProvenanceDestination(str(tmp_path / "provenance.json")),
    )
    assert not report.ready
    assert any("multiplier 1.5" in error for error in report.errors)

    protocol, pins = _fixture(tmp_path, status="frozen")
    protocol["budget_freeze"]["condition_budgets"]["equal_information"] = {
        "max_model_calls": 99,
        "max_cost_usd": 99,
    }
    pins = _repin_protocol(tmp_path, protocol, pins)
    incoherent = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="primary",
        resolved_model=_model(),
        condition_budgets=_budgets(frozen=True),
        pinned_refs=pins,
        mode="execute",
        environment={"MODEL_KEY": "TOP_SECRET_VALUE"},
        provenance_destination=ProvenanceDestination(str(tmp_path / "provenance.json")),
    )
    assert not incoherent.ready
    assert any("does not match frozen budget" in error for error in incoherent.errors)


def test_model_settings_are_hashed_then_discarded_and_placeholders_fail_execute(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="credential-like"):
        ExperimentModelIdentity(
            "alias", "provider", "model", settings={"api_key": "ALSO_SECRET"}
        )
    model = ExperimentModelIdentity(
        "alias",
        "provider",
        "model",
        settings={"metadata": {"value": "TOP_SECRET_VALUE"}},
    )
    encoded = repr(model) + str(model.as_dict())
    assert "TOP_SECRET_VALUE" not in encoded
    assert model.settings == {}

    protocol, pins = _fixture(tmp_path)
    report = preflight_experiment(
        repository_root=tmp_path,
        protocol=protocol,
        protocol_path="protocol.yaml",
        phase="calibration",
        resolved_model=ExperimentModelIdentity(
            "pre-key-placeholder",
            "provider-not-yet-selected",
            "model-not-yet-selected",
            credential_env="MODEL_KEY",
        ),
        condition_budgets=_budgets(),
        pinned_refs=pins,
        mode="execute",
        environment={"MODEL_KEY": "TOP_SECRET_VALUE"},
        provenance_destination=ProvenanceDestination(str(tmp_path / "provenance.json")),
    )
    assert not report.ready
    assert any("non-placeholder" in error for error in report.errors)
    assert "TOP_SECRET_VALUE" not in repr(report)
