"""Application-owned M03 agent role registry."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel

from .errors import UnknownAgent
from .models import (
    CriticFindingProposal,
    PermissionSet,
    PremiseCandidateProposal,
    SceneContractProposal,
    ScreenplayPatchProposal,
)


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    name: str
    model_alias: str
    output_model: type[BaseModel]
    output_artifact_type: str
    permissions: PermissionSet
    instructions: str


def _permissions(
    tools: set[str], *, read: set[str] | None = None, propose: set[str] | None = None
) -> PermissionSet:
    return PermissionSet(
        tools=frozenset(tools),
        read_artifacts=frozenset(read or set()),
        propose_artifacts=frozenset(propose or set()),
    )


DEFAULT_AGENTS = {
    "premise_candidate": AgentDefinition(
        "premise_candidate",
        "story_test",
        PremiseCandidateProposal,
        "premise_candidate",
        _permissions(
            {"retrieve_evidence", "read_skill_resource", "propose_artifact"},
            propose={"premise_candidate"},
        ),
        "Propose one evidence-grounded premise candidate.",
    ),
    "scene_contract": AgentDefinition(
        "scene_contract",
        "story_test",
        SceneContractProposal,
        "scene_contract",
        _permissions(
            {
                "read_artifact",
                "query_edges",
                "retrieve_evidence",
                "read_skill_resource",
                "propose_artifact",
            },
            read={"creative_constitution", "character", "relationship", "beat", "sequence"},
            propose={"scene_contract"},
        ),
        "Propose a causal Scene Contract without inventing unsupported facts.",
    ),
    "dialogue_patch": AgentDefinition(
        "dialogue_patch",
        "story_test",
        ScreenplayPatchProposal,
        "screenplay_patch",
        _permissions(
            {
                "read_artifact",
                "query_edges",
                "read_skill_resource",
                "propose_patch",
                "report_finding",
            },
            read={"scene_contract", "screenplay_scene", "character", "relationship"},
            propose={"screenplay_patch", "critic_finding"},
        ),
        "Propose a bounded screenplay patch preserving the approved Scene Contract.",
    ),
    "continuity_critic": AgentDefinition(
        "continuity_critic",
        "continuity_test",
        CriticFindingProposal,
        "critic_finding",
        _permissions(
            {
                "read_artifact",
                "query_edges",
                "retrieve_evidence",
                "read_skill_resource",
                "report_finding",
            },
            read={"scene_contract", "screenplay_scene", "character", "relationship", "beat"},
            propose={"critic_finding"},
        ),
        "Report a typed continuity finding; never approve or mutate canon.",
    ),
}


class AgentRegistry:
    def __init__(self, definitions: dict[str, AgentDefinition] | None = None) -> None:
        values = definitions or DEFAULT_AGENTS
        self._definitions = MappingProxyType(dict(values))

    def get(self, name: str) -> AgentDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise UnknownAgent(f"unknown agent role: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "model_alias": item.model_alias,
                "output_artifact_type": item.output_artifact_type,
                "tools": sorted(item.permissions.tools),
            }
            for name, item in sorted(self._definitions.items())
        }
