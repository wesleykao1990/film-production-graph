from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from film_graph.application import (
    CreateArtifactCommand,
    CreateProjectCommand,
    FilmGraphApplicationService,
    InMemoryGraphRepository,
    SelectPremiseCandidateCommand,
    StoryRoomApplicationService,
    TransitionVersionCommand,
)
from film_graph.application.errors import ConflictError, ValidationError
from film_graph.domain import (
    ActorRef,
    ActorType,
    ArtifactVersion,
    CausalBeat,
    KnowledgeDelta,
    LifecycleStatus,
    SceneContractSpec,
    SceneReaction,
    SceneRealization,
    SubtextPatchSpec,
    validate_causal_beat,
    validate_scene_contract,
    validate_scene_realization,
    validate_subtext_patch,
)
from film_graph.domain.errors import AuthorityError
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

HUMAN = ActorRef(ActorType.USER, "producer-1")
AGENT = ActorRef(ActorType.AGENT, "writer-1")


def test_causal_beat_requires_all_causal_fields() -> None:
    report = validate_causal_beat(CausalBeat(actor="Mara"))

    assert not report.valid
    assert {finding.path for finding in report.findings} == {
        "choice",
        "delta",
        "objective",
        "outcome",
    }
    assert report.as_dict()["findings"] == [item.as_dict() for item in report.findings]


def test_scene_contract_has_hard_objective_opposition_turn_and_state_delta_gate() -> None:
    report = validate_scene_contract(SceneContractSpec(character_refs=("mara",)))

    assert not report.valid
    codes = {(item.path, item.code) for item in report.findings}
    assert ("objective", "required") in codes
    assert ("opposition", "required") in codes
    assert ("turn", "required") in codes
    assert ("start_state", "required") in codes
    assert ("end_state", "required") in codes
    assert ("state_delta", "state_delta_required") in codes


def test_scene_realization_rejects_unknown_facts_entities_and_knowledge() -> None:
    realization = SceneRealization(
        scene_id="S01",
        used_entity_refs=("mara", "unknown-character"),
        used_fact_refs=("secret", "unknown-fact"),
        reactions=(
            SceneReaction("mara", "secret", "flinches", order=0),
            SceneReaction("mara", "secret", "answers", order=2),
        ),
    )
    report = validate_scene_realization(
        realization,
        allowed_entity_refs={"mara"},
        allowed_fact_refs={"secret"},
        initial_knowledge={"mara": ()},
        knowledge_deltas=(KnowledgeDelta("mara", "secret", order=1),),
    )

    assert not report.valid
    assert any(item.code == "unsupported_entity" for item in report.findings)
    assert any(item.code == "unsupported_fact" for item in report.findings)
    assert any(item.code == "unknown_fact" for item in report.findings)


def test_scene_knowledge_delta_order_makes_later_reaction_valid() -> None:
    realization = SceneRealization(
        scene_id="S01",
        used_entity_refs=("mara",),
        used_fact_refs=("secret",),
        reactions=(SceneReaction("mara", "secret", "answers", order=2),),
    )
    report = validate_scene_realization(
        realization,
        allowed_entity_refs={"mara"},
        allowed_fact_refs={"secret"},
        initial_knowledge={"mara": ()},
        knowledge_deltas=(KnowledgeDelta("mara", "secret", order=1),),
    )

    assert report.valid


def test_scene_realization_rejects_same_order_learning_and_reaction() -> None:
    report = validate_scene_realization(
        SceneRealization(
            scene_id="S01",
            used_entity_refs=("mara",),
            used_fact_refs=("secret",),
            reactions=(SceneReaction("mara", "secret", "answers", order=1),),
        ),
        allowed_entity_refs={"mara"},
        allowed_fact_refs={"secret"},
        initial_knowledge={"mara": ()},
        knowledge_deltas=(KnowledgeDelta("mara", "secret", order=1),),
    )

    assert not report.valid
    assert any(item.code == "ambiguous_event_order" for item in report.findings)


def test_scene_contract_projection_matches_authoritative_schema() -> None:
    contract = SceneContractSpec(
        scene_id="S01",
        sequence_id="SEQ01",
        source_beat_ids=("B01",),
        objective="Mara must leave with the key.",
        opposition="Ivo blocks the only exit.",
        turn="Mara trades the ledger for passage.",
        start_state={"location": "archive", "key": "held"},
        end_state={"location": "street", "key": "held"},
        character_refs=("mara", "ivo"),
        required_facts=("fact-key-exists",),
        knowledge_deltas=(KnowledgeDelta("mara", "fact-key-exists", order=1),),
        forbidden_changes=("do not reveal the ledger contents",),
        failure_conditions=("Mara leaves without the key.",),
    )
    assert validate_scene_contract(contract).valid
    schema_path = Path(__file__).resolve().parents[2] / "schemas/scene-contract.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(contract.as_dict())) == []


def test_subtext_patch_is_bounded_to_scope_and_preserves_entities_and_outcome() -> None:
    target = uuid4()
    outcome = {"choice": "keep the key"}
    valid = SubtextPatchSpec(
        patch_id="patch-1",
        target_version_id=target,
        allowed_scope=("dialogue",),
        original_outcome=outcome,
        result_outcome=outcome,
        original_entity_refs=("mara", "ivo"),
        result_entity_refs=("mara", "ivo"),
        changed_fields=("dialogue",),
    )
    assert validate_subtext_patch(valid, target_version_id=target, locked_outcome=outcome).valid

    invalid = SubtextPatchSpec(
        patch_id="patch-2",
        target_version_id=uuid4(),
        allowed_scope=("dialogue",),
        original_outcome=outcome,
        result_outcome={"choice": "leave"},
        original_entity_refs=("mara",),
        result_entity_refs=("mara", "new-character"),
        changed_fields=("dialogue", "outcome"),
    )
    report = validate_subtext_patch(
        invalid,
        target_version_id=target,
        locked_outcome=outcome,
    )
    assert {item.code for item in report.findings} == {
        "new_entity",
        "outcome_changed",
        "patch_scope",
        "patch_target",
    }


def _premise(
    service: FilmGraphApplicationService,
    project_id: UUID,
    key: str,
    actor: ActorRef = HUMAN,
) -> ArtifactVersion:
    return service.create_artifact(
        CreateArtifactCommand(
            project_id,
            "premise_candidate",
            key,
            {"title": key, "logline": f"A premise about {key}"},
            actor,
        )
    )


def _to_human_review(service: FilmGraphApplicationService, version_id: UUID) -> None:
    for status in (LifecycleStatus.VALIDATED, LifecycleStatus.HUMAN_REVIEW):
        service.transition_version(
            TransitionVersionCommand(version_id, status, HUMAN, expected_current_revision=1)
        )


def test_human_selection_approves_only_selected_branch_and_keeps_rejected_branch() -> None:
    repository = InMemoryGraphRepository()
    graph = FilmGraphApplicationService(repository)
    story_room = StoryRoomApplicationService(graph)
    project = graph.create_project(CreateProjectCommand("Story Room"))
    first = _premise(graph, project.id, "Blue Pen")
    second = _premise(graph, project.id, "Red Thread")
    _to_human_review(graph, first.id)
    _to_human_review(graph, second.id)

    selected = story_room.select_premise_candidate(
        SelectPremiseCandidateCommand(
            project.id,
            (first.id, second.id),
            first.id,
            1,
            HUMAN,
            "The first candidate makes the causal thesis testable.",
        )
    )

    assert selected.lifecycle_status is LifecycleStatus.APPROVED
    rejected = repository.get_version(second.id)
    assert rejected is not None
    assert rejected.lifecycle_status is LifecycleStatus.HUMAN_REVIEW
    rationale = repository.human_decisions[-1].rationale
    assert rationale is not None
    assert rationale.startswith("The first candidate")


def test_selection_rejects_foreign_or_non_premise_versions_without_mutating_branches() -> None:
    repository = InMemoryGraphRepository()
    graph = FilmGraphApplicationService(repository)
    story_room = StoryRoomApplicationService(graph)
    project = graph.create_project(CreateProjectCommand("Local"))
    foreign_project = graph.create_project(CreateProjectCommand("Foreign"))
    local = _premise(graph, project.id, "Local premise")
    foreign = _premise(graph, foreign_project.id, "Foreign premise")
    _to_human_review(graph, local.id)
    _to_human_review(graph, foreign.id)

    with pytest.raises(ValidationError, match="requested project"):
        story_room.select_premise_candidate(
            SelectPremiseCandidateCommand(
                project.id, (local.id, foreign.id), local.id, 1, HUMAN, "keep local"
            )
        )
    unchanged = repository.get_version(local.id)
    assert unchanged is not None
    assert unchanged.lifecycle_status is LifecycleStatus.HUMAN_REVIEW


def test_selection_requires_human_rationale_two_distinct_candidates_and_revision() -> None:
    repository = InMemoryGraphRepository()
    graph = FilmGraphApplicationService(repository)
    story_room = StoryRoomApplicationService(graph)
    project = graph.create_project(CreateProjectCommand("Rules"))
    first = _premise(graph, project.id, "one")
    second = _premise(graph, project.id, "two")
    _to_human_review(graph, first.id)
    _to_human_review(graph, second.id)

    with pytest.raises(AuthorityError):
        story_room.select_premise_candidate(
            SelectPremiseCandidateCommand(
                project.id, (first.id, second.id), first.id, 1, AGENT, "agent choice"
            )
        )
    with pytest.raises(ValidationError, match="rationale"):
        story_room.select_premise_candidate(
            SelectPremiseCandidateCommand(
                project.id, (first.id, second.id), first.id, 1, HUMAN, "  "
            )
        )
    with pytest.raises(ValidationError, match="at least two"):
        story_room.select_premise_candidate(
            SelectPremiseCandidateCommand(project.id, (first.id,), first.id, 1, HUMAN, "one")
        )
    with pytest.raises(ValidationError, match="distinct"):
        story_room.select_premise_candidate(
            SelectPremiseCandidateCommand(
                project.id, (first.id, first.id), first.id, 1, HUMAN, "duplicate"
            )
        )
    with pytest.raises(ConflictError):
        story_room.select_premise_candidate(
            SelectPremiseCandidateCommand(
                project.id, (first.id, second.id), first.id, 2, HUMAN, "stale revision"
            )
        )
