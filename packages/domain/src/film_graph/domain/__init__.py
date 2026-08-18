"""Dependency-free M01 domain values and invariants."""

from dataclasses import dataclass
from typing import Literal

from .actors import ActorRef, ActorType
from .artifacts import INITIAL_ARTIFACT_TYPES, ArtifactIdentity, ArtifactVersion
from .entities import (
    EDGE_TYPES,
    INITIAL_EDGE_TYPES,
    ArtifactEdge,
    Asset,
    AssetVersion,
    HumanDecision,
    Project,
    ProjectEvent,
    ProviderPolicy,
    ProviderPolicySnapshot,
    RunRecord,
)
from .errors import (
    AuthorityError,
    DomainError,
    InvalidActor,
    InvalidLifecycleTransition,
    InvalidRights,
    RightsRequired,
)
from .hashing import canonical_json, canonical_value, content_hash, to_json_compatible
from .impact import ImpactRecord
from .lifecycle import (
    ImpactClassification,
    ImpactResolutionStatus,
    LifecycleStatus,
    allowed_transitions,
    validate_transition,
)
from .rights import PermittedUse, RightsRecord, RightsSourceType, RightsStatus


@dataclass(frozen=True, slots=True)
class FoundationBoundary:
    """Backward-compatible M00 marker retained for the reference suite."""

    milestone: Literal["M00"] = "M00"
    canonical_store: Literal["postgres"] = "postgres"
    agents_may_approve: Literal[False] = False


__all__ = [
    "ActorRef",
    "ActorType",
    "ArtifactIdentity",
    "ArtifactEdge",
    "ArtifactVersion",
    "EDGE_TYPES",
    "INITIAL_EDGE_TYPES",
    "Asset",
    "AssetVersion",
    "AuthorityError",
    "DomainError",
    "FoundationBoundary",
    "HumanDecision",
    "INITIAL_ARTIFACT_TYPES",
    "ImpactClassification",
    "ImpactRecord",
    "ImpactResolutionStatus",
    "InvalidActor",
    "InvalidLifecycleTransition",
    "InvalidRights",
    "LifecycleStatus",
    "RightsRecord",
    "RightsRequired",
    "RightsSourceType",
    "RightsStatus",
    "Project",
    "ProjectEvent",
    "ProviderPolicy",
    "ProviderPolicySnapshot",
    "PermittedUse",
    "RunRecord",
    "allowed_transitions",
    "canonical_json",
    "canonical_value",
    "content_hash",
    "to_json_compatible",
    "validate_transition",
]
