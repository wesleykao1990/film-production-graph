from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest
from film_graph.application import (
    ApproveAssetCommand,
    CreateArtifactCommand,
    CreateAssetCommand,
    CreateEdgeCommand,
    CreateProjectCommand,
    CreateRightsCommand,
    FilmGraphApplicationService,
    InMemoryGraphRepository,
    ResolveImpactCommand,
    ReviseArtifactCommand,
    TransitionVersionCommand,
)
from film_graph.application.errors import ConflictError
from film_graph.domain import (
    ActorRef,
    ActorType,
    ArtifactVersion,
    ImpactClassification,
    ImpactResolutionStatus,
    LifecycleStatus,
    Project,
    RightsRecord,
    RightsSourceType,
    RightsStatus,
)
from film_graph.domain.errors import AuthorityError


@pytest.fixture
def graph() -> tuple[
    FilmGraphApplicationService, InMemoryGraphRepository, Project, ActorRef
]:
    repository = InMemoryGraphRepository()
    service = FilmGraphApplicationService(repository)
    project = service.create_project(CreateProjectCommand("M01 Test"))
    return service, repository, project, ActorRef(ActorType.USER, "human")


def create_artifact(
    service: FilmGraphApplicationService,
    project_id: UUID,
    artifact_type: str,
    key: str,
    actor: ActorRef,
) -> ArtifactVersion:
    return service.create_artifact(
        CreateArtifactCommand(project_id, artifact_type, key, {"key": key}, actor)
    )


def lock(
    service: FilmGraphApplicationService, version_id: UUID, actor: ActorRef
) -> None:
    for status in (
        LifecycleStatus.VALIDATED,
        LifecycleStatus.HUMAN_REVIEW,
        LifecycleStatus.APPROVED,
        LifecycleStatus.LOCKED,
    ):
        service.transition_version(TransitionVersionCommand(version_id, status, actor, 1))


def test_revision_concurrency_and_locked_payload_invariant(
    graph: tuple[FilmGraphApplicationService, InMemoryGraphRepository, Project, ActorRef],
) -> None:
    service, repository, project, actor = graph
    version = create_artifact(service, project.id, "creative_constitution", "constitution", actor)
    lock(service, version.id, actor)
    revised = service.revise_artifact(
        ReviseArtifactCommand(version.artifact_id, {"key": "new"}, actor, 1)
    )
    assert revised.revision == 2
    assert revised.parent_version_id == version.id
    with pytest.raises(ConflictError):
        service.revise_artifact(
            ReviseArtifactCommand(version.artifact_id, {"key": "stale"}, actor, 1)
        )
    with pytest.raises(ConflictError):
        service.transition_version(
            TransitionVersionCommand(version.id, LifecycleStatus.DEPRECATED, actor, 2)
        )
    original = repository.get_version(version.id)
    assert original is not None
    assert original.payload["key"] == "constitution"


def test_lifecycle_mutation_requires_current_revision(
    graph: tuple[FilmGraphApplicationService, InMemoryGraphRepository, Project, ActorRef],
) -> None:
    service, repository, project, actor = graph
    version = create_artifact(service, project.id, "sequence", "concurrency", actor)
    with pytest.raises(ConflictError, match="expected 2, current 1"):
        service.transition_version(
            TransitionVersionCommand(
                version.id,
                LifecycleStatus.VALIDATED,
                actor,
                expected_current_revision=2,
            )
        )


def test_reachable_impacts_are_idempotent_and_do_not_change_lifecycle(
    graph: tuple[FilmGraphApplicationService, InMemoryGraphRepository, Project, ActorRef],
) -> None:
    service, repository, project, actor = graph
    constitution = create_artifact(
        service, project.id, "creative_constitution", "constitution", actor
    )
    sequence = create_artifact(service, project.id, "sequence", "sequence", actor)
    scene = create_artifact(service, project.id, "scene_contract", "scene", actor)
    unrelated = create_artifact(service, project.id, "evidence_item", "unrelated", actor)
    service.create_edge(CreateEdgeCommand(project.id, constitution.id, sequence.id))
    service.create_edge(CreateEdgeCommand(project.id, sequence.id, scene.id))
    lock(service, sequence.id, actor)
    revised = service.revise_artifact(
        ReviseArtifactCommand(constitution.artifact_id, {"key": "changed"}, actor, 1)
    )
    service.transition_version(
        TransitionVersionCommand(revised.id, LifecycleStatus.VALIDATED, actor, 2)
    )
    service.transition_version(
        TransitionVersionCommand(revised.id, LifecycleStatus.HUMAN_REVIEW, actor, 2)
    )
    service.transition_version(
        TransitionVersionCommand(revised.id, LifecycleStatus.APPROVED, actor, 2)
    )
    service.transition_version(
        TransitionVersionCommand(revised.id, LifecycleStatus.LOCKED, actor, 2)
    )
    impacts = service.list_impacts(project.id)
    assert {item.affected_version_id for item in impacts} == {sequence.id, scene.id}
    assert all(item.cause_version_id == revised.id for item in impacts)
    assert len({(item.cause_version_id, item.affected_version_id) for item in impacts}) == 2
    stored_sequence = repository.get_version(sequence.id)
    stored_unrelated = repository.get_version(unrelated.id)
    assert stored_sequence is not None
    assert stored_unrelated is not None
    assert stored_sequence.lifecycle_status is LifecycleStatus.LOCKED
    assert stored_unrelated.lifecycle_status is LifecycleStatus.DRAFT

    first = impacts[0]
    resolved = service.resolve_impact(
        ResolveImpactCommand(
            first.id,
            ImpactClassification.REVIEWED_VALID,
            ImpactResolutionStatus.RESOLVED,
            actor,
        )
    )
    assert resolved.classification is ImpactClassification.REVIEWED_VALID
    assert resolved.resolution_status is ImpactResolutionStatus.RESOLVED
    contradictory = service.validate_impact(
        first.id,
        contradicted=True,
        finding="finding-1",
        actor=ActorRef(ActorType.SYSTEM, "validator"),
    )
    assert contradictory.classification is ImpactClassification.CONTRADICTED
    assert contradictory.resolution_status is ImpactResolutionStatus.RESOLVED


def test_edges_reject_cycles_and_cross_project_links(
    graph: tuple[FilmGraphApplicationService, InMemoryGraphRepository, Project, ActorRef],
) -> None:
    service, _, project, actor = graph
    left = create_artifact(service, project.id, "sequence", "left", actor)
    right = create_artifact(service, project.id, "sequence", "right", actor)
    service.create_edge(CreateEdgeCommand(project.id, left.id, right.id))
    with pytest.raises(ConflictError, match="cycle"):
        service.create_edge(CreateEdgeCommand(project.id, right.id, left.id))
    other = service.create_project(CreateProjectCommand("Other"))
    foreign = create_artifact(service, other.id, "sequence", "foreign", actor)
    with pytest.raises(ConflictError, match="cross-project"):
        service.create_edge(CreateEdgeCommand(project.id, left.id, foreign.id))


def test_asset_approval_requires_rights_and_human_actor(
    graph: tuple[FilmGraphApplicationService, InMemoryGraphRepository, Project, ActorRef],
) -> None:
    service, repository, project, actor = graph
    asset = service.create_asset(
        CreateAssetCommand(project.id, "reference_image", "hero", {"bytes": "hash"}, actor)
    )
    stored_version = next(iter(repository.asset_versions.values()))
    with pytest.raises(FrozenInstanceError):
        stored_version.revision = 2  # type: ignore[misc]
    agent = ActorRef(ActorType.AGENT, "agent-1")
    with pytest.raises(AuthorityError):
        service.approve_asset(ApproveAssetCommand(asset.id, agent))
    with pytest.raises(ConflictError, match="rights"):
        service.approve_asset(ApproveAssetCommand(asset.id, actor))
    rights = RightsRecord.create(
        project_id=project.id,
        subject_ref=str(asset.id),
        status=RightsStatus.DECLARED,
        source_type=RightsSourceType.LICENSED,
        holder="Studio",
        permitted_uses=["film_tv"],
        territories=["worldwide"],
        reviewed_by="human",
        reviewed_at=datetime.now(UTC),
    )
    agent_rights = RightsRecord.create(
        project_id=project.id,
        subject_ref=str(asset.id),
        status=RightsStatus.DECLARED,
        source_type=RightsSourceType.LICENSED,
        holder="Studio",
        permitted_uses=["film_tv"],
        territories=["worldwide"],
        reviewed_by="agent-1",
        reviewed_at=datetime.now(UTC),
    )
    with pytest.raises(AuthorityError):
        service.create_rights(CreateRightsCommand(agent_rights, agent))
    unverified_agent_rights = RightsRecord.create(
        project_id=project.id,
        subject_ref=str(asset.id),
        status=RightsStatus.UNVERIFIED,
        source_type=RightsSourceType.UNKNOWN,
        holder="Pending claimant",
        permitted_uses=["film_tv"],
        territories=["worldwide"],
        reviewed_by=None,
        reviewed_at=None,
    )
    service.create_rights(CreateRightsCommand(unverified_agent_rights, agent))
    assert repository.rights_attesters[unverified_agent_rights.id] == agent
    logical_key_rights = RightsRecord.create(
        project_id=project.id,
        subject_ref="hero",
        status=RightsStatus.DECLARED,
        source_type=RightsSourceType.LICENSED,
        holder="Studio",
        permitted_uses=["film_tv"],
        territories=["worldwide"],
        reviewed_by="human",
        reviewed_at=datetime.now(UTC),
    )
    service.create_rights(CreateRightsCommand(logical_key_rights, actor))
    with pytest.raises(ConflictError, match="rights"):
        service.approve_asset(ApproveAssetCommand(asset.id, actor))
    service.create_rights(CreateRightsCommand(rights, actor))
    approved = service.approve_asset(ApproveAssetCommand(asset.id, actor))
    assert approved.lifecycle_status is LifecycleStatus.APPROVED


def test_hash_normalizes_timezones_and_unicode() -> None:
    from film_graph.domain import content_hash

    assert content_hash(
        {"text": "e\u0301\r\n", "when": "2026-01-01T09:00:00+09:00"}
    ) == content_hash({"when": "2026-01-01T00:00:00Z", "text": "é\n"})
