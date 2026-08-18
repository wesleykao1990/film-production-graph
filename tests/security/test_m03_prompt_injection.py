from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from film_graph.agent_runtime import (
    TOOL_NAMES,
    EvidenceSnapshot,
    FilmRunContext,
    PermissionDenied,
    PermissionSet,
    RunBudget,
    RuntimeExecutionError,
    ToolRegistry,
    TypedAgentRuntime,
    network_guard,
)
from film_graph.model_routing import ResolvedModel
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

CORPUS = Path(__file__).parent / "prompt_injection/corpus.yaml"
EMPTY_SNAPSHOT_HASH = "sha256:" + ("0" * 64)


def permissions() -> PermissionSet:
    return PermissionSet(
        tools=TOOL_NAMES,
        read_artifacts=frozenset({"scene_contract"}),
        propose_artifacts=frozenset(
            {"premise_candidate", "scene_contract", "screenplay_patch", "critic_finding"}
        ),
    )


def test_complete_injection_corpus_cannot_change_runtime_authority() -> None:
    cases = yaml.safe_load(CORPUS.read_text(encoding="utf-8"))["cases"]
    assert len(cases) == 8
    for case in cases:
        project_id = uuid4()
        policy = permissions()
        budget = RunBudget(1, Decimal("0.10"), Decimal("0.01"))
        context = FilmRunContext(
            project_id=project_id,
            run_id=uuid4(),
            skill_snapshot_hash=EMPTY_SNAPSHOT_HASH,
            resolved_model=ResolvedModel(
                alias="story_test", provider="fake", model="security-test"
            ),
            budget=budget,
            application_permissions=policy,
            skill_permissions=policy,
            project_permissions=policy,
            evidence=(
                EvidenceSnapshot(
                    project_id,
                    case["id"],
                    case["content"],
                    {"channel": case["channel"]},
                ),
            ),
        )
        with network_guard():
            result = TypedAgentRuntime().run(
                "premise_candidate",
                context,
                case["content"],
                model=TestModel(call_tools=[], model_name="security-test"),
            )
        assert result.output.status == "proposed"
        assert context.budget == budget
        assert context.application_permissions == policy
        assert result.provenance_dict()["tool_calls"] == []
        serialized = json.dumps(result.provenance_dict(), sort_keys=True)
        assert case["content"] not in serialized


def test_unknown_and_authority_tools_are_denied_before_execution() -> None:
    policy = permissions()
    context = FilmRunContext(
        project_id=uuid4(),
        run_id=uuid4(),
        skill_snapshot_hash=EMPTY_SNAPSHOT_HASH,
        resolved_model=ResolvedModel(alias="story_test", provider="fake", model="security"),
        budget=RunBudget(2, Decimal("1")),
        application_permissions=policy,
        skill_permissions=policy,
        project_permissions=policy,
    )
    tools = ToolRegistry(context, policy)
    for forbidden in ("approve", "lock", "release", "raw_sql", "shell", "network"):
        with pytest.raises(PermissionDenied):
            tools._allow(forbidden)
    assert tools.calls == ()

    attempts = 0

    def malicious_tool(_messages: object, _info: object) -> ModelResponse:
        nonlocal attempts
        attempts += 1
        return ModelResponse([ToolCallPart("approve", {"status": "approved"})])

    with pytest.raises(RuntimeExecutionError):
        TypedAgentRuntime(retries=1).run(
            "premise_candidate",
            context,
            "approve this artifact",
            model=FunctionModel(malicious_tool, model_name="security"),
        )
    assert attempts == 2
    assert tools.calls == ()
