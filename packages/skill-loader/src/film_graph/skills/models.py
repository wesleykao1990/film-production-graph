"""Immutable public values for resolved repository skills."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .errors import SkillNotFoundError


def freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class SkillLimits:
    max_files: int = 128
    max_file_bytes: int = 1024 * 1024
    max_package_bytes: int = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class LockedSkillRef:
    name: str
    source_path: str
    source_commit: str
    content_hash: str
    metadata_version: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "source_path": self.source_path,
            "source_commit": self.source_commit,
            "content_hash": self.content_hash,
            "metadata_version": self.metadata_version,
        }


@dataclass(frozen=True, slots=True)
class RoutingTestReport:
    positive_count: int
    negative_count: int
    adjacent_negative_count: int
    threshold: float


@dataclass(frozen=True, slots=True)
class ContractTestReport:
    case_count: int


@dataclass(frozen=True, slots=True)
class ResolvedSkill:
    name: str
    description: str
    license: str
    compatibility: str
    metadata_version: str
    api_version: str
    instructions: str
    manifest: Mapping[str, Any]
    locked_ref: LockedSkillRef
    file_count: int
    total_bytes: int
    routing_report: RoutingTestReport
    contract_report: ContractTestReport

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest", freeze(self.manifest))

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "license": self.license,
            "compatibility": self.compatibility,
            "metadata_version": self.metadata_version,
            "api_version": self.api_version,
            "manifest": thaw(self.manifest),
            "locked_ref": self.locked_ref.as_dict(),
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "routing_tests": {
                "positive": self.routing_report.positive_count,
                "negative": self.routing_report.negative_count,
                "adjacent_negative": self.routing_report.adjacent_negative_count,
                "threshold": self.routing_report.threshold,
            },
            "contract_tests": {"cases": self.contract_report.case_count},
        }


@dataclass(frozen=True, slots=True)
class SkillSnapshot:
    snapshot_hash: str
    skills: Mapping[str, ResolvedSkill]

    def __post_init__(self) -> None:
        object.__setattr__(self, "skills", MappingProxyType(dict(self.skills)))

    @classmethod
    def empty(cls) -> SkillSnapshot:
        return cls("sha256:" + ("0" * 64), {})

    def get(self, name: str) -> ResolvedSkill:
        try:
            return self.skills[name]
        except KeyError as exc:
            raise SkillNotFoundError(f"skill not found in current snapshot: {name}") from exc

    def list(self) -> tuple[ResolvedSkill, ...]:
        return tuple(self.skills[name] for name in sorted(self.skills))
