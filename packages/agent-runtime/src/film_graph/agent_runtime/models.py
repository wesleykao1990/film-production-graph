"""Immutable M03 context values and strict proposal contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Literal, cast
from uuid import UUID

from film_graph.model_routing import ResolvedModel
from pydantic import BaseModel, ConfigDict, Field

SHA256_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


def freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, frozenset)):
        return [thaw(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


class StrictProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: Literal["proposed"] = "proposed"


class PremiseCandidateProposal(StrictProposal):
    output_type: Literal["premise_candidate"] = "premise_candidate"
    title: str = Field(min_length=1)
    logline: str = Field(min_length=1)
    dramatic_question: str = Field(min_length=1)


class SceneContractProposal(StrictProposal):
    output_type: Literal["scene_contract"] = "scene_contract"
    objective: str = Field(min_length=1)
    opposition: str = Field(min_length=1)
    turn: str = Field(min_length=1)
    state_delta: str = Field(min_length=1)
    knowledge_delta: str = Field(min_length=1)
    forbidden_changes: tuple[str, ...] = ()


class ScreenplayPatchProposal(StrictProposal):
    output_type: Literal["screenplay_patch"] = "screenplay_patch"
    target_version_id: UUID
    replacement_text: str = Field(min_length=1)
    invariants: tuple[str, ...] = ()


class CriticFindingProposal(StrictProposal):
    output_type: Literal["critic_finding"] = "critic_finding"
    rule_id: str = Field(min_length=1)
    severity: Literal["info", "warning", "error"]
    message: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()


AgentProposal = (
    PremiseCandidateProposal
    | SceneContractProposal
    | ScreenplayPatchProposal
    | CriticFindingProposal
)


@dataclass(frozen=True, slots=True)
class ArtifactSnapshot:
    project_id: UUID
    artifact_id: UUID
    version_id: UUID
    artifact_type: str
    content_hash: str
    payload: Mapping[str, Any]
    lifecycle_status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze(self.payload))


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    project_id: UUID
    evidence_id: str
    content: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", freeze(self.metadata))


@dataclass(frozen=True, slots=True)
class EdgeSnapshot:
    project_id: UUID
    from_version_id: UUID
    to_version_id: UUID
    edge_type: str


@dataclass(frozen=True, slots=True)
class SkillRef:
    name: str
    source_path: str
    source_commit: str
    content_hash: str
    metadata_version: str
    snapshot_hash: str

    def __post_init__(self) -> None:
        if not SHA256_PATTERN.fullmatch(self.content_hash):
            raise ValueError("skill content_hash must be a sha256 digest")
        if not SHA256_PATTERN.fullmatch(self.snapshot_hash):
            raise ValueError("skill snapshot_hash must be a sha256 digest")

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "source_path": self.source_path,
            "source_commit": self.source_commit,
            "content_hash": self.content_hash,
            "metadata_version": self.metadata_version,
            "snapshot_hash": self.snapshot_hash,
        }


@dataclass(frozen=True, slots=True)
class PermissionSet:
    tools: frozenset[str] = frozenset()
    read_artifacts: frozenset[str] = frozenset()
    propose_artifacts: frozenset[str] = frozenset()

    @classmethod
    def intersect(cls, *values: PermissionSet) -> PermissionSet:
        if not values:
            return cls()
        return cls(
            tools=frozenset.intersection(*(item.tools for item in values)),
            read_artifacts=frozenset.intersection(
                *(item.read_artifacts for item in values)
            ),
            propose_artifacts=frozenset.intersection(
                *(item.propose_artifacts for item in values)
            ),
        )


@dataclass(frozen=True, slots=True)
class RunBudget:
    max_model_calls: int
    max_cost_usd: Decimal
    estimated_call_cost_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.max_model_calls < 0:
            raise ValueError("max_model_calls must be non-negative")
        if self.max_cost_usd < 0 or self.estimated_call_cost_usd < 0:
            raise ValueError("cost budgets must be non-negative")


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    name: str
    arguments_hash: str
    result_hash: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "arguments_hash": self.arguments_hash,
            "result_hash": self.result_hash,
        }


@dataclass(frozen=True, slots=True)
class FilmRunContext:
    project_id: UUID
    run_id: UUID
    skill_snapshot_hash: str
    resolved_model: ResolvedModel
    budget: RunBudget
    application_permissions: PermissionSet
    skill_permissions: PermissionSet
    project_permissions: PermissionSet
    artifacts: tuple[ArtifactSnapshot, ...] = ()
    evidence: tuple[EvidenceSnapshot, ...] = ()
    edges: tuple[EdgeSnapshot, ...] = ()
    skill_refs: tuple[SkillRef, ...] = ()
    skill_instructions: Mapping[str, str] = field(default_factory=dict)
    skill_resources: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not SHA256_PATTERN.fullmatch(self.skill_snapshot_hash):
            raise ValueError("skill_snapshot_hash must be a sha256 digest")
        if any(item.snapshot_hash != self.skill_snapshot_hash for item in self.skill_refs):
            raise ValueError("skill refs must match the resolved skill snapshot")
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "skill_refs", tuple(self.skill_refs))
        object.__setattr__(self, "skill_instructions", freeze(self.skill_instructions))
        object.__setattr__(self, "skill_resources", freeze(self.skill_resources))


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    output: AgentProposal
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", freeze(self.provenance))

    def provenance_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], thaw(self.provenance))
