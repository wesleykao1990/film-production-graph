"""Artifact lifecycle and independent impact states."""

from __future__ import annotations

from enum import StrEnum

from .errors import InvalidLifecycleTransition


class LifecycleStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    HUMAN_REVIEW = "human_review"
    APPROVED = "approved"
    LOCKED = "locked"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class ImpactClassification(StrEnum):
    POSSIBLY_STALE = "possibly_stale"
    CONTRADICTED = "contradicted"
    REVIEWED_VALID = "reviewed_valid"
    REDERIVE_REQUESTED = "rederive_requested"
    RESOLVED = "resolved"


class ImpactResolutionStatus(StrEnum):
    UNRESOLVED = "unresolved"
    ACKNOWLEDGED = "acknowledged"
    REVALIDATE_REQUESTED = "revalidate_requested"
    REDERIVE_REQUESTED = "rederive_requested"
    RESOLVED = "resolved"


_ALLOWED_TRANSITIONS: dict[LifecycleStatus, frozenset[LifecycleStatus]] = {
    LifecycleStatus.DRAFT: frozenset({LifecycleStatus.VALIDATED}),
    LifecycleStatus.VALIDATED: frozenset({LifecycleStatus.HUMAN_REVIEW}),
    LifecycleStatus.HUMAN_REVIEW: frozenset({LifecycleStatus.APPROVED, LifecycleStatus.REJECTED}),
    LifecycleStatus.APPROVED: frozenset({LifecycleStatus.LOCKED}),
    # Locked versions are immutable.  A future deprecation command can create
    # a new decision/version without mutating this row.
    LifecycleStatus.LOCKED: frozenset(),
    LifecycleStatus.REJECTED: frozenset(),
    LifecycleStatus.DEPRECATED: frozenset(),
}


def allowed_transitions(status: LifecycleStatus) -> frozenset[LifecycleStatus]:
    return _ALLOWED_TRANSITIONS[LifecycleStatus(status)]


def validate_transition(current: LifecycleStatus, target: LifecycleStatus) -> None:
    current = LifecycleStatus(current)
    target = LifecycleStatus(target)
    if target not in allowed_transitions(current):
        raise InvalidLifecycleTransition(
            f"cannot transition version from {current.value!r} to {target.value!r}"
        )
