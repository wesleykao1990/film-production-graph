"""Immutable artifact identity/version value objects."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid4

from .actors import ActorRef
from .hashing import canonical_value, content_hash, to_json_compatible
from .lifecycle import LifecycleStatus

_SCHEMA_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?$")

INITIAL_ARTIFACT_TYPES: frozenset[str] = frozenset(
    {
        "creative_constitution",
        "evidence_item",
        "premise_candidate",
        "character",
        "relationship",
        "beat",
        "sequence",
        "scene_contract",
        "screenplay_scene",
        "screenplay_patch",
        "critic_finding",
        "delivery_spec",
        "budget_plan",
    }
)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    return to_json_compatible(value)


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    id: UUID
    project_id: UUID
    artifact_type: str
    logical_key: str

    def __post_init__(self) -> None:
        if self.artifact_type not in INITIAL_ARTIFACT_TYPES:
            raise ValueError(f"unsupported M01 artifact type: {self.artifact_type}")
        if not self.logical_key.strip():
            raise ValueError("logical_key must not be empty")


@dataclass(frozen=True, slots=True)
class ArtifactVersion:
    id: UUID
    artifact_id: UUID
    project_id: UUID
    schema_version: str
    revision: int
    lifecycle_status: LifecycleStatus
    payload: Mapping[str, Any]
    content_hash: str
    created_by: ActorRef
    created_at: datetime
    parent_version_id: UUID | None = None
    provenance: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "lifecycle_status", LifecycleStatus(self.lifecycle_status))
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        if not _SCHEMA_VERSION_PATTERN.fullmatch(self.schema_version):
            raise ValueError(
                "schema_version must match major.minor or major.minor.patch"
            )
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        frozen = _freeze(canonical_value(self.payload))
        object.__setattr__(self, "payload", frozen)
        expected = content_hash(_thaw(frozen))
        if self.content_hash != expected:
            raise ValueError("content_hash does not match canonical payload")
        if self.provenance is not None:
            object.__setattr__(self, "provenance", _freeze(canonical_value(self.provenance)))

    @classmethod
    def create(
        cls,
        *,
        artifact_id: UUID,
        project_id: UUID,
        payload: Mapping[str, Any],
        created_by: ActorRef,
        schema_version: str = "1.0",
        revision: int = 1,
        lifecycle_status: LifecycleStatus = LifecycleStatus.DRAFT,
        parent_version_id: UUID | None = None,
        version_id: UUID | None = None,
        created_at: datetime | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> ArtifactVersion:
        normalized = canonical_value(payload)
        return cls(
            id=version_id or uuid4(),
            artifact_id=artifact_id,
            project_id=project_id,
            schema_version=schema_version,
            revision=revision,
            lifecycle_status=lifecycle_status,
            payload=_freeze(normalized),
            content_hash=content_hash(normalized),
            created_by=created_by,
            created_at=created_at or datetime.now(UTC),
            parent_version_id=parent_version_id,
            provenance=provenance,
        )

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "artifact_id": str(self.artifact_id),
            "version_id": str(self.id),
            "project_id": str(self.project_id),
            "schema_version": self.schema_version,
            "revision": self.revision,
            "lifecycle_status": self.lifecycle_status.value,
            "payload": _thaw(self.payload),
            "content_hash": self.content_hash,
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "created_by": self.created_by.as_dict(),
            "created_at": self.created_at.astimezone(UTC).isoformat(),
        }
        if self.provenance is not None:
            result["provenance"] = _thaw(self.provenance)
        return result
