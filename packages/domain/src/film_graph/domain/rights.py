"""Rights value objects and approval gate."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .errors import InvalidRights


class RightsStatus(StrEnum):
    UNVERIFIED = "unverified"
    DECLARED = "declared"
    CLEARED = "cleared"
    RESTRICTED = "restricted"
    EXPIRED = "expired"
    REJECTED = "rejected"


class RightsSourceType(StrEnum):
    SELF_CREATED = "self_created"
    LICENSED = "licensed"
    PUBLIC_DOMAIN = "public_domain"
    PROVIDER_GENERATED = "provider_generated"
    COMMISSIONED = "commissioned"
    CONSENTED_VOICE = "consented_voice"
    CONSENTED_LIKENESS = "consented_likeness"
    UNKNOWN = "unknown"


class PermittedUse(StrEnum):
    INTERNAL_DEVELOPMENT = "internal_development"
    FESTIVAL = "festival"
    STREAMING = "streaming"
    COMMERCIAL_DISTRIBUTION = "commercial_distribution"
    ADVERTISING = "advertising"
    FILM_TV = "film_tv"
    GAMES = "games"
    SOCIAL_MEDIA = "social_media"
    TRAINING = "training"


@dataclass(frozen=True, slots=True)
class RightsRecord:
    id: UUID
    project_id: UUID
    subject_ref: str
    status: RightsStatus
    source_type: RightsSourceType
    holder: str
    permitted_uses: frozenset[PermittedUse]
    territories: tuple[str, ...]
    reviewed_by: str | None
    reviewed_at: datetime | None
    license_or_permission: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    attribution: str | None = None
    evidence_asset_refs: tuple[str, ...] = ()
    consent_record_refs: tuple[str, ...] = ()
    provider_policy_ref: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", RightsStatus(self.status))
        object.__setattr__(self, "source_type", RightsSourceType(self.source_type))
        if not self.subject_ref.strip() or not self.holder.strip():
            raise InvalidRights("rights subject_ref and holder are required")
        try:
            uses = frozenset(PermittedUse(str(value).strip()) for value in self.permitted_uses)
        except ValueError as exc:
            raise InvalidRights("unsupported permitted use") from exc
        territories = tuple(str(value).strip() for value in self.territories if str(value).strip())
        if not uses or not territories:
            raise InvalidRights("rights permitted_uses and territories are required")
        object.__setattr__(self, "permitted_uses", uses)
        object.__setattr__(self, "territories", territories)
        for timestamp_name in ("reviewed_at", "starts_at", "expires_at"):
            timestamp = getattr(self, timestamp_name)
            if timestamp is not None and timestamp.tzinfo is None:
                raise InvalidRights(f"{timestamp_name} must be timezone-aware")
        if (
            self.status in {RightsStatus.DECLARED, RightsStatus.CLEARED}
            and (self.reviewed_at is None or not self.reviewed_by)
        ):
            raise InvalidRights("declared/cleared rights require reviewer and review time")
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise InvalidRights("rights expiry must be after start")

    @classmethod
    def create(
        cls,
        *,
        project_id: UUID,
        subject_ref: str,
        status: RightsStatus,
        source_type: RightsSourceType,
        holder: str,
        permitted_uses: Iterable[str | PermittedUse],
        territories: Iterable[str],
        reviewed_by: str | None,
        reviewed_at: datetime | None,
        rights_record_id: UUID | None = None,
        **kwargs: Any,
    ) -> RightsRecord:
        try:
            normalized_uses = frozenset(PermittedUse(str(value)) for value in permitted_uses)
        except ValueError as exc:
            raise InvalidRights("unsupported permitted use") from exc
        return cls(
            id=rights_record_id or uuid4(),
            project_id=project_id,
            subject_ref=subject_ref,
            status=status,
            source_type=source_type,
            holder=holder,
            permitted_uses=normalized_uses,
            territories=tuple(territories),
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            **kwargs,
        )

    @property
    def permits_approval(self) -> bool:
        return self.status in {RightsStatus.DECLARED, RightsStatus.CLEARED}

    def as_dict(self) -> dict[str, Any]:
        return {
            "rights_record_id": str(self.id),
            "subject_ref": self.subject_ref,
            "status": self.status.value,
            "source_type": self.source_type.value,
            "holder": self.holder,
            "permitted_uses": sorted(item.value for item in self.permitted_uses),
            "territories": list(self.territories),
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "license_or_permission": self.license_or_permission,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "attribution": self.attribution,
            "evidence_asset_refs": list(self.evidence_asset_refs),
            "consent_record_refs": list(self.consent_record_refs),
            "provider_policy_ref": self.provider_policy_ref,
            "notes": list(self.notes),
        }
