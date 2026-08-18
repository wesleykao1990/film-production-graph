"""Small M01 entity values beyond artifact versions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from .actors import ActorRef
from .artifacts import _freeze, _thaw
from .hashing import canonical_value, content_hash
from .lifecycle import LifecycleStatus

EDGE_TYPES: frozenset[str] = frozenset(
    {
        "DERIVED_FROM",
        "REQUIRES",
        "IMPLEMENTS",
        "USES_ASSET",
        "PAYS_OFF",
        "CONTRADICTS",
        "SUPERSEDES",
        "SELECTED_FROM",
    }
)
INITIAL_EDGE_TYPES = EDGE_TYPES


@dataclass(frozen=True, slots=True)
class Project:
    id: UUID
    name: str
    created_at: datetime

    @classmethod
    def create(cls, name: str, *, project_id: UUID | None = None) -> Project:
        if not name.strip():
            raise ValueError("project name must not be empty")
        return cls(project_id or uuid4(), name.strip(), datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ArtifactEdge:
    project_id: UUID
    from_version_id: UUID
    to_version_id: UUID
    edge_type: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.from_version_id == self.to_version_id:
            raise ValueError("an artifact edge cannot point to itself")
        if self.edge_type not in EDGE_TYPES:
            raise ValueError(f"unsupported artifact edge type: {self.edge_type!r}")
        object.__setattr__(self, "metadata", _freeze(canonical_value(self.metadata)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "from_version_id": str(self.from_version_id),
            "to_version_id": str(self.to_version_id),
            "edge_type": self.edge_type,
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class Asset:
    id: UUID
    project_id: UUID
    asset_type: str
    logical_key: str
    lifecycle_status: LifecycleStatus
    created_by: ActorRef
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AssetVersion:
    id: UUID
    asset_id: UUID
    project_id: UUID
    revision: int
    payload: Mapping[str, Any]
    content_hash: str
    created_by: ActorRef
    created_at: datetime

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("asset revision must be >= 1")
        normalized = canonical_value(self.payload)
        object.__setattr__(self, "payload", _freeze(normalized))
        if self.content_hash != content_hash(normalized):
            raise ValueError("asset content_hash does not match payload")


@dataclass(frozen=True, slots=True)
class RunRecord:
    id: UUID
    project_id: UUID
    model_alias: str | None
    resolved_provider: str | None
    resolved_model: str | None
    provenance: Mapping[str, Any]
    disposition: str
    created_by: ActorRef
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", _freeze(canonical_value(self.provenance)))


@dataclass(frozen=True, slots=True)
class ProviderPolicy:
    id: UUID
    project_id: UUID
    provider: str
    model_or_service: str | None
    captured_at: datetime
    source_url_or_document_ref: str | None
    commercial_use_status: str
    retention_training_status: str
    voice_likeness_constraints: tuple[str, ...]
    distribution_constraints: tuple[str, ...]
    allowed_for_project: bool
    block_reasons: tuple[str, ...]

    COMMERCIAL_USE_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {"allowed", "restricted", "unknown", "disallowed"}
    )
    RETENTION_TRAINING_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {"no_training", "opt_out_configured", "may_train", "unknown"}
    )

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        if self.commercial_use_status not in self.COMMERCIAL_USE_STATUSES:
            raise ValueError("unsupported commercial_use_status")
        if self.retention_training_status not in self.RETENTION_TRAINING_STATUSES:
            raise ValueError("unsupported retention_training_status")
        object.__setattr__(
            self,
            "voice_likeness_constraints",
            tuple(str(item) for item in self.voice_likeness_constraints),
        )
        object.__setattr__(
            self,
            "distribution_constraints",
            tuple(str(item) for item in self.distribution_constraints),
        )
        object.__setattr__(self, "block_reasons", tuple(str(item) for item in self.block_reasons))

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_policy_id": str(self.id),
            "project_id": str(self.project_id),
            "provider": self.provider,
            "model_or_service": self.model_or_service,
            "captured_at": self.captured_at.astimezone(UTC).isoformat(),
            "source_url_or_document_ref": self.source_url_or_document_ref,
            "commercial_use_status": self.commercial_use_status,
            "retention_training_status": self.retention_training_status,
            "voice_likeness_constraints": list(self.voice_likeness_constraints),
            "distribution_constraints": list(self.distribution_constraints),
            "allowed_for_project": self.allowed_for_project,
            "block_reasons": list(self.block_reasons),
        }


@dataclass(frozen=True, slots=True)
class HumanDecision:
    id: UUID
    project_id: UUID
    subject_ref: str
    decision_type: str
    actor: ActorRef
    rationale: str | None
    created_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_id": str(self.id),
            "project_id": str(self.project_id),
            "subject_ref": self.subject_ref,
            "decision_type": self.decision_type,
            "actor": self.actor.as_dict(),
            "rationale": self.rationale,
            "created_at": self.created_at.astimezone(UTC).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ProjectEvent:
    id: UUID
    project_id: UUID
    event_type: str
    subject_ref: str | None
    payload: Mapping[str, Any]
    created_by: ActorRef
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _freeze(canonical_value(self.payload)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.id),
            "project_id": str(self.project_id),
            "event_type": self.event_type,
            "subject_ref": self.subject_ref,
            "payload": _thaw(self.payload),
            "created_by": self.created_by.as_dict(),
            "created_at": self.created_at.astimezone(UTC).isoformat(),
        }


ProviderPolicySnapshot = ProviderPolicy
