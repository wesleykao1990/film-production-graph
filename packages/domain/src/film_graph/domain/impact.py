"""Impact record value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from .actors import ActorRef
from .lifecycle import ImpactClassification, ImpactResolutionStatus


@dataclass(frozen=True, slots=True)
class ImpactRecord:
    id: UUID
    project_id: UUID
    cause_version_id: UUID
    affected_version_id: UUID
    classification: ImpactClassification
    resolution_status: ImpactResolutionStatus
    reason: str | None
    validator_finding_ids: tuple[str, ...]
    created_at: datetime
    resolved_by: ActorRef | None = None
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "classification", ImpactClassification(self.classification))
        object.__setattr__(
            self, "resolution_status", ImpactResolutionStatus(self.resolution_status)
        )
        if self.cause_version_id == self.affected_version_id:
            raise ValueError("an impact record cannot affect its cause version")

    @classmethod
    def create(
        cls,
        *,
        project_id: UUID,
        cause_version_id: UUID,
        affected_version_id: UUID,
        reason: str | None = None,
        classification: ImpactClassification = ImpactClassification.POSSIBLY_STALE,
        impact_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> ImpactRecord:
        return cls(
            id=impact_id or uuid4(),
            project_id=project_id,
            cause_version_id=cause_version_id,
            affected_version_id=affected_version_id,
            classification=classification,
            resolution_status=ImpactResolutionStatus.UNRESOLVED,
            reason=reason,
            validator_finding_ids=(),
            created_at=created_at or datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "impact_id": str(self.id),
            "project_id": str(self.project_id),
            "cause_version_id": str(self.cause_version_id),
            "affected_version_id": str(self.affected_version_id),
            "classification": self.classification.value,
            "resolution_status": self.resolution_status.value,
            "reason": self.reason,
            "validator_finding_ids": list(self.validator_finding_ids),
            "resolved_by": self.resolved_by.as_dict() if self.resolved_by else None,
            "created_at": self.created_at.astimezone(UTC).isoformat(),
            "resolved_at": self.resolved_at.astimezone(UTC).isoformat()
            if self.resolved_at
            else None,
        }
