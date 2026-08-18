"""Seven typed, project-scoped M03 tools with no authority escalation path."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar
from uuid import UUID

from pydantic_ai import RunContext

from .errors import PermissionDenied, ProjectScopeViolation
from .models import FilmRunContext, PermissionSet, ToolCallRecord, thaw

TOOL_NAMES = frozenset(
    {
        "read_artifact",
        "query_edges",
        "retrieve_evidence",
        "read_skill_resource",
        "propose_artifact",
        "propose_patch",
        "report_finding",
    }
)
T = TypeVar("T")


def _hash(value: Any) -> str:
    encoded = json.dumps(
        thaw(value), sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class ToolRegistry:
    context: FilmRunContext
    permissions: PermissionSet
    _calls: list[ToolCallRecord] = field(default_factory=list, init=False)

    @property
    def names(self) -> frozenset[str]:
        return TOOL_NAMES

    @property
    def calls(self) -> tuple[ToolCallRecord, ...]:
        return tuple(self._calls)

    def _allow(self, name: str) -> None:
        if name not in TOOL_NAMES or name not in self.permissions.tools:
            raise PermissionDenied(f"tool is not in the effective permission set: {name}")

    def _record(self, name: str, arguments: Any, result: T) -> T:
        self._calls.append(ToolCallRecord(name, _hash(arguments), _hash(result)))
        return result

    def read_artifact(self, version_id: str) -> dict[str, Any]:
        self._allow("read_artifact")
        wanted = UUID(version_id)
        for item in self.context.artifacts:
            if item.version_id != wanted:
                continue
            if item.project_id != self.context.project_id:
                raise ProjectScopeViolation("artifact belongs to another project")
            if item.artifact_type not in self.permissions.read_artifacts:
                raise PermissionDenied(f"artifact type is not readable: {item.artifact_type}")
            result = {
                "artifact_id": str(item.artifact_id),
                "version_id": str(item.version_id),
                "artifact_type": item.artifact_type,
                "content_hash": item.content_hash,
                "lifecycle_status": item.lifecycle_status,
                "payload": thaw(item.payload),
            }
            return self._record("read_artifact", {"version_id": version_id}, result)
        raise PermissionDenied("artifact version is not an input to this run")

    def query_edges(self, version_id: str) -> list[dict[str, str]]:
        self._allow("query_edges")
        wanted = UUID(version_id)
        result: list[dict[str, str]] = []
        for edge in self.context.edges:
            if wanted in {edge.from_version_id, edge.to_version_id}:
                if edge.project_id != self.context.project_id:
                    raise ProjectScopeViolation("edge belongs to another project")
                result.append(
                    {
                        "from_version_id": str(edge.from_version_id),
                        "to_version_id": str(edge.to_version_id),
                        "edge_type": edge.edge_type,
                    }
                )
        return self._record("query_edges", {"version_id": version_id}, result)

    def retrieve_evidence(self, evidence_id: str) -> dict[str, Any]:
        self._allow("retrieve_evidence")
        for item in self.context.evidence:
            if item.evidence_id != evidence_id:
                continue
            if item.project_id != self.context.project_id:
                raise ProjectScopeViolation("evidence belongs to another project")
            result = {
                "evidence_id": item.evidence_id,
                "content": item.content,
                "metadata": thaw(item.metadata),
                "trust": "untrusted_content",
            }
            return self._record(
                "retrieve_evidence", {"evidence_id": evidence_id}, result
            )
        raise PermissionDenied("evidence is not an input to this run")

    def read_skill_resource(self, skill_name: str, resource_path: str) -> str:
        self._allow("read_skill_resource")
        resources = self.context.skill_resources.get(skill_name)
        if resources is None or resource_path not in resources:
            raise PermissionDenied("skill resource is not preloaded from the locked package")
        result = str(resources[resource_path])
        return self._record(
            "read_skill_resource",
            {"skill_name": skill_name, "resource_path": resource_path},
            result,
        )

    def propose_artifact(self, artifact_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._allow("propose_artifact")
        if artifact_type not in self.permissions.propose_artifacts:
            raise PermissionDenied(f"artifact type is not proposal-allowed: {artifact_type}")
        result = {"artifact_type": artifact_type, "status": "proposed", "payload": dict(payload)}
        return self._record("propose_artifact", {"artifact_type": artifact_type}, result)

    def propose_patch(
        self, target_version_id: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        self._allow("propose_patch")
        if "screenplay_patch" not in self.permissions.propose_artifacts:
            raise PermissionDenied("screenplay_patch is not proposal-allowed")
        target = self.read_artifact(target_version_id)
        result = {
            "artifact_type": "screenplay_patch",
            "status": "proposed",
            "target_version_id": target["version_id"],
            "payload": dict(payload),
        }
        return self._record(
            "propose_patch", {"target_version_id": target_version_id}, result
        )

    def report_finding(self, rule_id: str, severity: str, message: str) -> dict[str, str]:
        self._allow("report_finding")
        if severity not in {"info", "warning", "error"}:
            raise PermissionDenied("finding severity is not allowed")
        result = {
            "artifact_type": "critic_finding",
            "status": "proposed",
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
        }
        return self._record(
            "report_finding", {"rule_id": rule_id, "severity": severity}, result
        )


@dataclass(slots=True)
class RuntimeDeps:
    tools: ToolRegistry


def read_artifact(ctx: RunContext[RuntimeDeps], version_id: str) -> dict[str, Any]:
    return ctx.deps.tools.read_artifact(version_id)


def query_edges(ctx: RunContext[RuntimeDeps], version_id: str) -> list[dict[str, str]]:
    return ctx.deps.tools.query_edges(version_id)


def retrieve_evidence(ctx: RunContext[RuntimeDeps], evidence_id: str) -> dict[str, Any]:
    return ctx.deps.tools.retrieve_evidence(evidence_id)


def read_skill_resource(
    ctx: RunContext[RuntimeDeps], skill_name: str, resource_path: str
) -> str:
    return ctx.deps.tools.read_skill_resource(skill_name, resource_path)


def propose_artifact(
    ctx: RunContext[RuntimeDeps], artifact_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return ctx.deps.tools.propose_artifact(artifact_type, payload)


def propose_patch(
    ctx: RunContext[RuntimeDeps], target_version_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return ctx.deps.tools.propose_patch(target_version_id, payload)


def report_finding(
    ctx: RunContext[RuntimeDeps], rule_id: str, severity: str, message: str
) -> dict[str, str]:
    return ctx.deps.tools.report_finding(rule_id, severity, message)


PYDANTIC_TOOLS = {
    item.__name__: item
    for item in (
        read_artifact,
        query_edges,
        retrieve_evidence,
        read_skill_resource,
        propose_artifact,
        propose_patch,
        report_finding,
    )
}
