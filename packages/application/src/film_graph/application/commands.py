"""Explicit application commands for the M01 core."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from film_graph.domain import (
    ActorRef,
    ImpactClassification,
    ImpactResolutionStatus,
    LifecycleStatus,
    RightsRecord,
)


@dataclass(frozen=True, slots=True)
class CreateProjectCommand:
    name: str
    project_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class BindProjectSkillCommand:
    """Bind one resolved skill reference to an agent in a project."""

    project_id: UUID
    agent_ref: str
    skill_name: str
    source_path: str
    source_commit: str
    content_hash: str
    metadata_version: str
    snapshot_hash: str
    actor: ActorRef
    binding_id: UUID | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CreateArtifactCommand:
    project_id: UUID
    artifact_type: str
    logical_key: str
    payload: Mapping[str, Any]
    actor: ActorRef
    schema_version: str = "1.0"
    provenance: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ReviseArtifactCommand:
    artifact_id: UUID
    payload: Mapping[str, Any]
    actor: ActorRef
    expected_current_revision: int
    schema_version: str | None = None
    provenance: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TransitionVersionCommand:
    version_id: UUID
    target_status: LifecycleStatus
    actor: ActorRef
    expected_current_revision: int
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class CreateEdgeCommand:
    project_id: UUID
    from_version_id: UUID
    to_version_id: UUID
    edge_type: str = "DERIVED_FROM"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResolveImpactCommand:
    impact_id: UUID
    classification: ImpactClassification
    resolution_status: ImpactResolutionStatus
    actor: ActorRef


@dataclass(frozen=True, slots=True)
class BulkResolveImpactsCommand:
    impact_ids: tuple[UUID, ...]
    classification: ImpactClassification
    resolution_status: ImpactResolutionStatus
    actor: ActorRef

    @classmethod
    def from_iterable(
        cls,
        impact_ids: Iterable[UUID],
        *,
        classification: ImpactClassification,
        resolution_status: ImpactResolutionStatus,
        actor: ActorRef,
    ) -> BulkResolveImpactsCommand:
        return cls(tuple(impact_ids), classification, resolution_status, actor)


@dataclass(frozen=True, slots=True)
class CreateAssetCommand:
    project_id: UUID
    asset_type: str
    logical_key: str
    payload: Mapping[str, Any]
    actor: ActorRef


@dataclass(frozen=True, slots=True)
class CreateRightsCommand:
    record: RightsRecord
    actor: ActorRef


@dataclass(frozen=True, slots=True)
class ApproveAssetCommand:
    asset_id: UUID
    actor: ActorRef


@dataclass(frozen=True, slots=True)
class CreateRunCommand:
    project_id: UUID
    actor: ActorRef
    provenance: Mapping[str, Any]
    model_alias: str | None = None
    resolved_provider: str | None = None
    resolved_model: str | None = None
    disposition: str = "completed"


@dataclass(frozen=True, slots=True)
class CreateProviderPolicyCommand:
    project_id: UUID
    provider: str
    captured_at: datetime
    commercial_use_status: str
    retention_training_status: str
    allowed_for_project: bool
    actor: ActorRef
    model_or_service: str | None = None
    source_url_or_document_ref: str | None = None
    voice_likeness_constraints: tuple[str, ...] = ()
    distribution_constraints: tuple[str, ...] = ()
    block_reasons: tuple[str, ...] = ()
    policy_id: UUID | None = None


CreateProviderPolicySnapshotCommand = CreateProviderPolicyCommand


@dataclass(frozen=True, slots=True)
class CreateProjectEventCommand:
    project_id: UUID
    event_type: str
    actor: ActorRef
    subject_ref: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: UUID | None = None
