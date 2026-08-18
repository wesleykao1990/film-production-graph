from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from film_graph.domain import (
    ActorRef,
    ActorType,
    ArtifactEdge,
    ArtifactVersion,
    FoundationBoundary,
    LifecycleStatus,
    PermittedUse,
    RightsRecord,
    RightsSourceType,
    RightsStatus,
    content_hash,
    validate_transition,
)


def test_foundation_boundary_records_m00_authority_invariants() -> None:
    boundary = FoundationBoundary()
    assert boundary.milestone == "M00"
    assert boundary.canonical_store == "postgres"
    assert boundary.agents_may_approve is False
    with pytest.raises(FrozenInstanceError):
        boundary.agents_may_approve = True  # type: ignore[assignment,misc]


def test_domain_source_has_no_framework_or_future_domain_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages/domain/src"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    lowered = source.lower()
    for forbidden in ("fastapi", "pydantic_ai", "supabase", "prototype", "provider sdk"):
        assert forbidden not in lowered


def test_m01_artifact_hash_is_stable_and_payload_is_immutable() -> None:
    payload = {"title": "Still Water", "line": "you\r\nalready knew"}
    artifact = ArtifactVersion.create(
        artifact_id=uuid4(),
        project_id=uuid4(),
        payload=payload,
        created_by=ActorRef(ActorType.USER, "writer"),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert artifact.content_hash == content_hash(
        {"line": "you\nalready knew", "title": "Still Water"}
    )
    with pytest.raises(TypeError):
        artifact.payload["title"] = "mutated"  # type: ignore[index]


def test_lifecycle_requires_explicit_human_review_path() -> None:
    validate_transition(LifecycleStatus.DRAFT, LifecycleStatus.VALIDATED)
    with pytest.raises(ValueError):
        validate_transition(LifecycleStatus.DRAFT, LifecycleStatus.APPROVED)


def test_domain_rejects_unknown_edge_and_schema_version() -> None:
    with pytest.raises(ValueError, match="edge type"):
        ArtifactEdge(uuid4(), uuid4(), uuid4(), "made_up")
    with pytest.raises(ValueError, match="schema_version"):
        ArtifactVersion.create(
            artifact_id=uuid4(),
            project_id=uuid4(),
            payload={"title": "bad"},
            created_by=ActorRef(ActorType.USER, "writer"),
            schema_version="v1",
        )


def test_rights_use_enum_and_timezone_invariants() -> None:
    project_id = uuid4()
    with pytest.raises(ValueError, match="permitted use"):
        RightsRecord.create(
            project_id=project_id,
            subject_ref="asset",
            status=RightsStatus.DECLARED,
            source_type=RightsSourceType.LICENSED,
            holder="Studio",
            permitted_uses=["not_a_use"],
            territories=["worldwide"],
            reviewed_by="human",
            reviewed_at=datetime.now(UTC),
        )
    with pytest.raises(ValueError, match="timezone"):
        RightsRecord.create(
            project_id=project_id,
            subject_ref="asset",
            status=RightsStatus.DECLARED,
            source_type=RightsSourceType.LICENSED,
            holder="Studio",
            permitted_uses=[PermittedUse.FILM_TV],
            territories=["worldwide"],
            reviewed_by="human",
            reviewed_at=datetime.now(),
            starts_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
