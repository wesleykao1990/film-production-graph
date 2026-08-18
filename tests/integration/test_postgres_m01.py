"""M01 Postgres exit-gate tests; run when FPG_DATABASE_URL points at reset DB."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

pytest.importorskip("psycopg")

from film_graph.application import (  # noqa: E402
    ApproveAssetCommand,
    BulkResolveImpactsCommand,
    CreateArtifactCommand,
    CreateAssetCommand,
    CreateEdgeCommand,
    CreateProjectCommand,
    CreateProjectEventCommand,
    CreateProviderPolicyCommand,
    CreateRightsCommand,
    CreateRunCommand,
    FilmGraphApplicationService,
    ReviseArtifactCommand,
    TransitionVersionCommand,
)
from film_graph.application.errors import ConflictError  # noqa: E402
from film_graph.domain import (  # noqa: E402
    ActorRef,
    ActorType,
    ArtifactVersion,
    ImpactClassification,
    ImpactResolutionStatus,
    LifecycleStatus,
    RightsRecord,
    RightsSourceType,
    RightsStatus,
)
from film_graph.persistence import PostgresGraphRepository  # noqa: E402


@pytest.fixture
def service() -> FilmGraphApplicationService:
    dsn = os.getenv("FPG_DATABASE_URL")
    if not dsn:
        pytest.skip("FPG_DATABASE_URL is not configured; Postgres integration is opt-in")
    repository = PostgresGraphRepository(dsn)
    # A configured database is part of the M01 gate. Connection or migration
    # failures must fail the run rather than quietly converting it to a skip.
    repository.ping()
    return FilmGraphApplicationService(repository)


def _lock(
    service: FilmGraphApplicationService,
    version: ArtifactVersion,
    actor: ActorRef,
) -> ArtifactVersion:
    current = version
    for status in (
        LifecycleStatus.VALIDATED,
        LifecycleStatus.HUMAN_REVIEW,
        LifecycleStatus.APPROVED,
        LifecycleStatus.LOCKED,
    ):
        current = service.transition_version(
            TransitionVersionCommand(
                current.id,
                status,
                actor,
                expected_current_revision=current.revision,
                rationale=f"M01 exit gate: {status.value}",
            )
        )
    return current


def _ids(items: list[ArtifactVersion]) -> set[UUID]:
    return {item.id for item in items}


def test_postgres_m01_exit_gate_persists_across_restart(
    service: FilmGraphApplicationService,
) -> None:
    actor = ActorRef(ActorType.USER, f"integration-{uuid4()}")
    validator = ActorRef(ActorType.SYSTEM, "deterministic-validator")
    project = service.create_project(CreateProjectCommand(f"M01 {uuid4()}"))

    constitution = service.create_artifact(
        CreateArtifactCommand(
            project.id,
            "creative_constitution",
            "constitution",
            {"title": "Blue Pen", "theme": "memory has a cost"},
            actor,
        )
    )
    evidence = service.create_artifact(
        CreateArtifactCommand(
            project.id,
            "evidence_item",
            "evidence",
            {"claim": "The pen appears in every recovered memory."},
            actor,
        )
    )
    sequence = service.create_artifact(
        CreateArtifactCommand(
            project.id, "sequence", "sequence", {"title": "The Audit"}, actor
        )
    )
    scene = service.create_artifact(
        CreateArtifactCommand(
            project.id, "scene_contract", "scene", {"title": "S07"}, actor
        )
    )

    service.create_edge(CreateEdgeCommand(project.id, constitution.id, evidence.id))
    service.create_edge(CreateEdgeCommand(project.id, constitution.id, sequence.id))
    service.create_edge(CreateEdgeCommand(project.id, evidence.id, sequence.id))
    service.create_edge(CreateEdgeCommand(project.id, sequence.id, scene.id))

    locked_constitution = _lock(service, constitution, actor)
    locked_evidence = _lock(service, evidence, actor)
    locked_sequence = _lock(service, sequence, actor)
    locked_scene = _lock(service, scene, actor)
    assert {
        locked_constitution.lifecycle_status,
        locked_evidence.lifecycle_status,
        locked_sequence.lifecycle_status,
        locked_scene.lifecycle_status,
    } == {LifecycleStatus.LOCKED}

    revised = service.revise_artifact(
        ReviseArtifactCommand(
            constitution.artifact_id,
            {"title": "Blue Pen", "theme": "remembering always transfers a cost"},
            actor,
            expected_current_revision=1,
        )
    )
    revised = _lock(service, revised, actor)

    impacts = service.list_impacts(project.id)
    assert {item.affected_version_id for item in impacts} == {
        evidence.id,
        sequence.id,
        scene.id,
    }
    assert all(item.cause_version_id == revised.id for item in impacts)
    assert all(
        service.get_version(version_id)[1].lifecycle_status is LifecycleStatus.LOCKED
        for version_id in (evidence.id, sequence.id, scene.id)
    )

    by_affected = {item.affected_version_id: item for item in impacts}
    reviewed_valid = service.bulk_resolve_impacts(
        BulkResolveImpactsCommand.from_iterable(
            [by_affected[evidence.id].id],
            classification=ImpactClassification.REVIEWED_VALID,
            resolution_status=ImpactResolutionStatus.RESOLVED,
            actor=actor,
        )
    )[0]
    rederive = service.bulk_resolve_impacts(
        BulkResolveImpactsCommand.from_iterable(
            [by_affected[sequence.id].id],
            classification=ImpactClassification.REDERIVE_REQUESTED,
            resolution_status=ImpactResolutionStatus.REDERIVE_REQUESTED,
            actor=actor,
        )
    )[0]
    contradicted = service.validate_impact(
        by_affected[scene.id].id,
        contradicted=True,
        finding="theme-language-mismatch",
        actor=validator,
    )
    assert reviewed_valid.classification is ImpactClassification.REVIEWED_VALID
    assert rederive.resolution_status is ImpactResolutionStatus.REDERIVE_REQUESTED
    assert contradicted.classification is ImpactClassification.CONTRADICTED

    assert _ids(service.lineage(constitution.id, direction="downstream")) == {
        constitution.id,
        evidence.id,
        sequence.id,
        scene.id,
    }
    assert _ids(service.lineage(scene.id, direction="upstream")) == {
        constitution.id,
        evidence.id,
        sequence.id,
        scene.id,
    }

    asset = service.create_asset(
        CreateAssetCommand(
            project.id,
            "reference_image",
            "hero-reference",
            {"content_hash": "a" * 64},
            actor,
        )
    )
    with pytest.raises(ConflictError, match="rights"):
        service.approve_asset(ApproveAssetCommand(asset.id, actor))
    repository = service.repository
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
    service.create_rights(CreateRightsCommand(unverified_agent_rights, validator))
    with repository._scope() as connection:  # type: ignore[attr-defined]
        unverified_attester = connection.execute(
            """
            select attested_by_actor_type, attested_by_actor_id
              from public.rights_records where id = %s
            """,
            (unverified_agent_rights.id,),
        ).fetchone()
    assert unverified_attester == {
        "attested_by_actor_type": "system",
        "attested_by_actor_id": validator.actor_id,
    }
    logical_key_rights = RightsRecord.create(
        project_id=project.id,
        subject_ref="hero-reference",
        status=RightsStatus.DECLARED,
        source_type=RightsSourceType.LICENSED,
        holder="M01 Test Studio",
        permitted_uses=["film_tv"],
        territories=["worldwide"],
        reviewed_by=actor.actor_id,
        reviewed_at=datetime.now(UTC),
    )
    service.create_rights(CreateRightsCommand(logical_key_rights, actor))
    with pytest.raises(ConflictError, match="rights"):
        service.approve_asset(ApproveAssetCommand(asset.id, actor))
    rights = RightsRecord.create(
        project_id=project.id,
        subject_ref=str(asset.id),
        status=RightsStatus.DECLARED,
        source_type=RightsSourceType.LICENSED,
        holder="M01 Test Studio",
        permitted_uses=["film_tv"],
        territories=["worldwide"],
        reviewed_by=actor.actor_id,
        reviewed_at=datetime.now(UTC),
    )
    service.create_rights(CreateRightsCommand(rights, actor))
    with repository._scope() as connection:  # type: ignore[attr-defined]
        declared_attester = connection.execute(
            """
            select attested_by_actor_type, attested_by_actor_id
              from public.rights_records where id = %s
            """,
            (rights.id,),
        ).fetchone()
    assert declared_attester == {
        "attested_by_actor_type": "user",
        "attested_by_actor_id": actor.actor_id,
    }
    assert service.approve_asset(
        ApproveAssetCommand(asset.id, actor)
    ).lifecycle_status is LifecycleStatus.APPROVED

    with repository._scope() as connection:  # type: ignore[attr-defined]
        asset_version = connection.execute(
            "select id from public.asset_versions where asset_id = %s",
            (asset.id,),
        ).fetchone()
    assert asset_version is not None
    with pytest.raises(Exception, match="append-only"), repository._scope() as connection:  # type: ignore[attr-defined]
        connection.execute(
            "update public.asset_versions set revision = revision + 1 where id = %s",
            (asset_version["id"],),
        )
    with pytest.raises(Exception, match="append-only"), repository._scope() as connection:  # type: ignore[attr-defined]
        connection.execute(
            "delete from public.asset_versions where id = %s",
            (asset_version["id"],),
        )

    disposable_asset = service.create_asset(
        CreateAssetCommand(
            project.id,
            "reference_image",
            "cascade-cleanup",
            {"content_hash": "b" * 64},
            actor,
        )
    )
    with repository._scope() as connection:  # type: ignore[attr-defined]
        disposable_version = connection.execute(
            "select id from public.asset_versions where asset_id = %s",
            (disposable_asset.id,),
        ).fetchone()
    assert disposable_version is not None
    with repository._scope() as connection:  # type: ignore[attr-defined]
        connection.execute(
            "delete from public.assets where id = %s",
            (disposable_asset.id,),
        )
    with repository._scope() as connection:  # type: ignore[attr-defined]
        remaining_versions = connection.execute(
            "select count(*) as count from public.asset_versions where id = %s",
            (disposable_version["id"],),
        ).fetchone()
    assert remaining_versions["count"] == 0

    policy = service.create_provider_policy(
        CreateProviderPolicyCommand(
            project_id=project.id,
            provider="offline-fixture",
            captured_at=datetime.now(UTC),
            commercial_use_status="allowed",
            retention_training_status="no_training",
            allowed_for_project=True,
            actor=actor,
        )
    )
    service.create_run(
        CreateRunCommand(
            project_id=project.id,
            actor=actor,
            model_alias="offline",
            resolved_provider="fixture",
            resolved_model="deterministic",
            provenance={"input_version_ids": [str(constitution.id)]},
        )
    )
    event = service.create_project_event(
        CreateProjectEventCommand(
            project_id=project.id,
            event_type="m01_exit_gate_completed",
            actor=actor,
            subject_ref=str(revised.id),
            payload={"impact_count": len(impacts)},
        )
    )

    restarted = FilmGraphApplicationService(PostgresGraphRepository(os.environ["FPG_DATABASE_URL"]))
    loaded_identity, loaded = restarted.get_artifact(constitution.artifact_id)
    assert loaded_identity.project_id == project.id
    assert loaded.revision == 2
    assert loaded.lifecycle_status is LifecycleStatus.LOCKED
    assert restarted.list_provider_policies(project.id) == [policy]
    assert restarted.list_project_events(project.id) == [event]
    assert any(
        decision.subject_ref == str(revised.id)
        for decision in restarted.list_human_decisions(project.id)
    )
    with pytest.raises(ConflictError):
        restarted.revise_artifact(
            ReviseArtifactCommand(
                constitution.artifact_id,
                {"title": "stale"},
                actor,
                expected_current_revision=1,
            )
        )
