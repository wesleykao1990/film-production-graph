"""Pure, deterministic M04a Story Room contracts and hard validators.

These values deliberately carry references and IDs instead of trying to infer
story structure from prose.  Validation is a hard, ordered control; it does
not call a model, inspect a filesystem, or mutate repository state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal
from uuid import UUID

from .hashing import canonical_value, to_json_compatible


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


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


@dataclass(frozen=True, slots=True)
class StoryRoomFinding:
    """One deterministic validation finding."""

    code: str
    path: str
    message: str
    severity: Literal["error", "warning", "info"] = "error"

    def __post_init__(self) -> None:
        if self.severity not in {"error", "warning", "info"}:
            raise ValueError(f"unsupported Story Room finding severity: {self.severity!r}")

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class StoryRoomValidationReport:
    """Immutable, JSON-ready validator result with stable finding order."""

    valid: bool
    findings: tuple[StoryRoomFinding, ...] = ()

    def __post_init__(self) -> None:
        ordered = tuple(
            sorted(self.findings, key=lambda item: (item.path, item.code, item.message))
        )
        object.__setattr__(self, "findings", ordered)
        # Hard findings make a report invalid. Warning/info findings are
        # diagnostic only and may coexist with a valid report.
        object.__setattr__(self, "valid", not any(item.severity == "error" for item in ordered))

    @classmethod
    def from_findings(cls, findings: Iterable[StoryRoomFinding]) -> StoryRoomValidationReport:
        return cls(valid=False, findings=tuple(findings))

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "findings": [finding.as_dict() for finding in self.findings],
        }


# Short aliases make the report useful to callers that do not need the full
# milestone name while retaining one canonical implementation.
ValidationFinding = StoryRoomFinding
ValidationReport = StoryRoomValidationReport


@dataclass(frozen=True, slots=True)
class CausalBeat:
    """A causal beat whose required fields are checked by ``validate_causal_beat``."""

    beat_id: str = ""
    actor: str = ""
    objective: str = ""
    choice: str = ""
    outcome: str = ""
    delta: Mapping[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.beat_id

    def __post_init__(self) -> None:
        object.__setattr__(self, "delta", _freeze(canonical_value(self.delta)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "actor": self.actor,
            "objective": self.objective,
            "choice": self.choice,
            "outcome": self.outcome,
            "delta": to_json_compatible(self.delta),
        }


@dataclass(frozen=True, slots=True)
class KnowledgeDelta:
    """An explicitly ordered fact-knowledge change in a scene."""

    character_id: str = ""
    fact_id: str = ""
    known: bool = True
    order: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "fact_id": self.fact_id,
            "known": self.known,
            "order": self.order,
        }


@dataclass(frozen=True, slots=True)
class SceneContractSpec:
    """Minimum scene contract needed for the M04a hard gate."""

    scene_id: str = ""
    objective: str = ""
    opposition: str = ""
    turn: str = ""
    start_state: Mapping[str, Any] = field(default_factory=dict)
    end_state: Mapping[str, Any] = field(default_factory=dict)
    character_refs: tuple[str, ...] = ()
    required_facts: tuple[str, ...] = ()
    knowledge_deltas: tuple[KnowledgeDelta, ...] = ()
    forbidden_changes: tuple[str, ...] = ()
    state_delta: Mapping[str, Any] = field(default_factory=dict)
    sequence_id: str = ""
    source_beat_ids: tuple[str, ...] = ()
    failure_conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_state", _freeze(canonical_value(self.start_state)))
        object.__setattr__(self, "end_state", _freeze(canonical_value(self.end_state)))
        object.__setattr__(self, "state_delta", _freeze(canonical_value(self.state_delta)))
        object.__setattr__(self, "character_refs", tuple(str(item) for item in self.character_refs))
        object.__setattr__(self, "required_facts", tuple(str(item) for item in self.required_facts))
        object.__setattr__(
            self,
            "forbidden_changes",
            tuple(str(item) for item in self.forbidden_changes),
        )
        normalized_deltas: list[KnowledgeDelta] = []
        for item in self.knowledge_deltas:
            if isinstance(item, KnowledgeDelta):
                normalized_deltas.append(item)
            elif isinstance(item, Mapping):
                normalized_deltas.append(KnowledgeDelta(**dict(item)))
            else:
                raise TypeError("knowledge_deltas must contain KnowledgeDelta values")
        object.__setattr__(self, "knowledge_deltas", tuple(normalized_deltas))
        object.__setattr__(
            self, "source_beat_ids", tuple(str(item) for item in self.source_beat_ids)
        )
        object.__setattr__(
            self,
            "failure_conditions",
            tuple(str(item) for item in self.failure_conditions),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a projection compatible with ``scene-contract.schema.json``."""

        end_state = dict(to_json_compatible(self.end_state))
        if self.state_delta:
            end_state["state_delta"] = to_json_compatible(self.state_delta)
        if self.knowledge_deltas:
            end_state["knowledge_deltas"] = [item.as_dict() for item in self.knowledge_deltas]
        return {
            "scene_id": self.scene_id,
            "sequence_id": self.sequence_id,
            "source_beat_ids": list(self.source_beat_ids),
            "purpose": {
                "dramatic_question": self.objective,
                "sequence_function": self.opposition,
            },
            "objectives": {"primary": self.objective},
            "tactics": {"primary": {"initial": self.opposition}},
            "visible_engine": {"action": self.opposition},
            "turn": {
                "trigger": self.turn,
                "irreversible_choice": self.turn,
            },
            "start_state": to_json_compatible(self.start_state),
            "end_state": end_state,
            "required": {
                "facts": list(self.required_facts),
                "character_ids": list(self.character_refs),
            },
            "forbidden": list(self.forbidden_changes),
            "failure_conditions": list(self.failure_conditions),
        }

    def schema_projection(self) -> dict[str, Any]:
        """Explicit alias for callers documenting schema-bound serialization."""

        return self.as_dict()


@dataclass(frozen=True, slots=True)
class SceneReaction:
    character_id: str = ""
    fact_id: str = ""
    action: str = ""
    order: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "fact_id": self.fact_id,
            "action": self.action,
            "order": self.order,
        }


@dataclass(frozen=True, slots=True)
class SceneRealization:
    """A realization's explicit entity/fact references and reactions."""

    realization_id: str = ""
    scene_id: str = ""
    used_entity_refs: tuple[str, ...] = ()
    used_fact_refs: tuple[str, ...] = ()
    reactions: tuple[SceneReaction, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "used_entity_refs", tuple(str(item) for item in self.used_entity_refs)
        )
        object.__setattr__(self, "used_fact_refs", tuple(str(item) for item in self.used_fact_refs))
        normalized: list[SceneReaction] = []
        for item in self.reactions:
            if isinstance(item, SceneReaction):
                normalized.append(item)
            elif isinstance(item, Mapping):
                normalized.append(SceneReaction(**dict(item)))
            else:
                raise TypeError("reactions must contain SceneReaction values")
        object.__setattr__(self, "reactions", tuple(normalized))

    def as_dict(self) -> dict[str, Any]:
        return {
            "realization_id": self.realization_id,
            "scene_id": self.scene_id,
            "used_entity_refs": list(self.used_entity_refs),
            "used_fact_refs": list(self.used_fact_refs),
            "reactions": [item.as_dict() for item in self.reactions],
        }


@dataclass(frozen=True, slots=True)
class SubtextPatchSpec:
    """Bounded patch declaration preserving the locked scene outcome."""

    patch_id: str = ""
    target_version_id: UUID | str | None = None
    allowed_scope: tuple[str, ...] = ()
    original_outcome: Any = None
    result_outcome: Any = None
    original_entity_refs: tuple[str, ...] = ()
    result_entity_refs: tuple[str, ...] = ()
    changed_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_scope", tuple(str(item) for item in self.allowed_scope))
        object.__setattr__(
            self, "original_entity_refs", tuple(str(item) for item in self.original_entity_refs)
        )
        object.__setattr__(
            self, "result_entity_refs", tuple(str(item) for item in self.result_entity_refs)
        )
        object.__setattr__(self, "changed_fields", tuple(str(item) for item in self.changed_fields))
        object.__setattr__(
            self, "original_outcome", _freeze(canonical_value(self.original_outcome))
        )
        object.__setattr__(self, "result_outcome", _freeze(canonical_value(self.result_outcome)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "target_version_id": str(self.target_version_id)
            if self.target_version_id is not None
            else None,
            "allowed_scope": list(self.allowed_scope),
            "original_outcome": to_json_compatible(self.original_outcome),
            "result_outcome": to_json_compatible(self.result_outcome),
            "original_entity_refs": list(self.original_entity_refs),
            "result_entity_refs": list(self.result_entity_refs),
            "changed_fields": list(self.changed_fields),
        }


def _report(findings: Iterable[StoryRoomFinding]) -> StoryRoomValidationReport:
    return StoryRoomValidationReport.from_findings(findings)


def _required(findings: list[StoryRoomFinding], path: str, value: Any, label: str) -> None:
    if not _text(value):
        findings.append(StoryRoomFinding("required", path, f"{label} is required"))


def validate_causal_beat(beat: CausalBeat) -> StoryRoomValidationReport:
    findings: list[StoryRoomFinding] = []
    for name, label in (
        ("actor", "actor"),
        ("objective", "objective"),
        ("choice", "choice"),
        ("outcome", "outcome"),
    ):
        _required(findings, name, getattr(beat, name), label)
    if not isinstance(beat.delta, Mapping) or not beat.delta:
        findings.append(StoryRoomFinding("required", "delta", "delta must not be empty"))
    return _report(findings)


def validate_scene_contract(contract: SceneContractSpec) -> StoryRoomValidationReport:
    findings: list[StoryRoomFinding] = []
    for name in ("scene_id", "sequence_id", "objective", "opposition", "turn"):
        _required(findings, name, getattr(contract, name), name)
    if not contract.source_beat_ids:
        findings.append(
            StoryRoomFinding("required", "source_beat_ids", "source_beat_ids is required")
        )
    if not isinstance(contract.start_state, Mapping) or not contract.start_state:
        findings.append(StoryRoomFinding("required", "start_state", "start_state is required"))
    if not isinstance(contract.end_state, Mapping) or not contract.end_state:
        findings.append(StoryRoomFinding("required", "end_state", "end_state is required"))
    if not contract.state_delta and contract.start_state == contract.end_state:
        findings.append(
            StoryRoomFinding(
                "state_delta_required", "state_delta", "scene must declare a state delta"
            )
        )
    if not contract.character_refs:
        findings.append(
            StoryRoomFinding("required", "character_refs", "character_refs is required")
        )
    if not contract.required_facts:
        findings.append(
            StoryRoomFinding("required", "required_facts", "required_facts is required")
        )
    if not contract.knowledge_deltas:
        findings.append(
            StoryRoomFinding("required", "knowledge_deltas", "knowledge_deltas is required")
        )
    if not contract.forbidden_changes:
        findings.append(
            StoryRoomFinding("required", "forbidden_changes", "forbidden_changes is required")
        )
    if not contract.failure_conditions:
        findings.append(
            StoryRoomFinding("required", "failure_conditions", "failure_conditions is required")
        )
    orders = [item.order for item in contract.knowledge_deltas]
    if orders != sorted(orders) or len(set(orders)) != len(orders):
        findings.append(
            StoryRoomFinding(
                "knowledge_delta_order",
                "knowledge_deltas",
                "knowledge deltas must have unique ascending order values",
            )
        )
    for index, delta in enumerate(contract.knowledge_deltas):
        _required(
            findings, f"knowledge_deltas[{index}].character_id", delta.character_id, "character_id"
        )
        _required(findings, f"knowledge_deltas[{index}].fact_id", delta.fact_id, "fact_id")
    return _report(findings)


def _knowledge_events(
    initial_knowledge: Mapping[str, Iterable[str]],
    deltas: Sequence[KnowledgeDelta],
    reactions: Sequence[SceneReaction],
) -> tuple[dict[str, set[str]], list[tuple[int, int, str, Any]]]:
    knowledge = {
        str(character): {str(fact) for fact in facts}
        for character, facts in initial_knowledge.items()
    }
    events: list[tuple[int, int, str, Any]] = []
    for index, delta in enumerate(deltas):
        events.append((delta.order, index, "delta", delta))
    for index, reaction in enumerate(reactions):
        events.append((reaction.order, index, "reaction", reaction))
    events.sort(key=lambda item: (item[0], item[1], item[2]))
    return knowledge, events


def validate_scene_realization(
    realization: SceneRealization,
    *,
    allowed_entity_refs: Iterable[str],
    allowed_fact_refs: Iterable[str],
    initial_knowledge: Mapping[str, Iterable[str]] = {},
    knowledge_deltas: Sequence[KnowledgeDelta] = (),
) -> StoryRoomValidationReport:
    findings: list[StoryRoomFinding] = []
    entities = {str(item) for item in allowed_entity_refs}
    facts = {str(item) for item in allowed_fact_refs}
    events_orders = [
        *(item.order for item in knowledge_deltas),
        *(item.order for item in realization.reactions),
    ]
    if len(events_orders) != len(set(events_orders)):
        findings.append(
            StoryRoomFinding(
                "ambiguous_event_order",
                "knowledge_deltas/reactions",
                "knowledge deltas and reactions must have unique order values",
            )
        )
    for index, knowledge_delta in enumerate(knowledge_deltas):
        _required(
            findings,
            f"knowledge_deltas[{index}].character_id",
            knowledge_delta.character_id,
            "character_id",
        )
        _required(
            findings,
            f"knowledge_deltas[{index}].fact_id",
            knowledge_delta.fact_id,
            "fact_id",
        )
    for index, entity_ref in enumerate(realization.used_entity_refs):
        if entity_ref not in entities:
            findings.append(
                StoryRoomFinding(
                    "unsupported_entity",
                    f"used_entity_refs[{index}]",
                    f"unsupported entity: {entity_ref}",
                )
            )
    for index, fact_ref in enumerate(realization.used_fact_refs):
        if fact_ref not in facts:
            findings.append(
                StoryRoomFinding(
                    "unsupported_fact", f"used_fact_refs[{index}]", f"unsupported fact: {fact_ref}"
                )
            )
    knowledge, events = _knowledge_events(
        initial_knowledge, knowledge_deltas, realization.reactions
    )
    for _, _, event_type, event in events:
        if event_type == "delta":
            delta_event: KnowledgeDelta = event
            if delta_event.character_id not in knowledge:
                knowledge[delta_event.character_id] = set()
            if delta_event.known:
                knowledge[delta_event.character_id].add(delta_event.fact_id)
            else:
                knowledge[delta_event.character_id].discard(delta_event.fact_id)
            continue
        reaction: SceneReaction = event
        _required(findings, "reactions.character_id", reaction.character_id, "character_id")
        _required(findings, "reactions.fact_id", reaction.fact_id, "fact_id")
        _required(findings, "reactions.action", reaction.action, "action")
        if reaction.character_id not in entities:
            findings.append(
                StoryRoomFinding(
                    "unsupported_entity",
                    "reactions",
                    f"unsupported reacting character: {reaction.character_id}",
                )
            )
        if reaction.fact_id not in facts:
            findings.append(
                StoryRoomFinding(
                    "unsupported_fact",
                    "reactions",
                    f"unsupported reaction fact: {reaction.fact_id}",
                )
            )
        if reaction.fact_id not in knowledge.get(reaction.character_id, set()):
            findings.append(
                StoryRoomFinding(
                    "unknown_fact",
                    "reactions",
                    f"{reaction.character_id} cannot react to unknown fact {reaction.fact_id}",
                )
            )
    return _report(findings)


def validate_subtext_patch(
    patch: SubtextPatchSpec,
    *,
    target_version_id: UUID | str,
    locked_outcome: Any,
    allowed_scope: Iterable[str] | None = None,
) -> StoryRoomValidationReport:
    findings: list[StoryRoomFinding] = []
    if patch.target_version_id is None or str(patch.target_version_id) != str(target_version_id):
        findings.append(
            StoryRoomFinding(
                "patch_target",
                "target_version_id",
                "patch target does not match the requested version",
            )
        )
    if not patch.allowed_scope:
        findings.append(StoryRoomFinding("required", "allowed_scope", "allowed_scope is required"))
    if patch.original_outcome is None:
        findings.append(
            StoryRoomFinding("required", "original_outcome", "original_outcome is required")
        )
    if patch.result_outcome is None:
        findings.append(
            StoryRoomFinding("required", "result_outcome", "result_outcome is required")
        )
    scope = set(
        str(item) for item in (allowed_scope if allowed_scope is not None else patch.allowed_scope)
    )
    unsupported = sorted(set(patch.changed_fields) - scope)
    if unsupported:
        findings.append(
            StoryRoomFinding(
                "patch_scope",
                "changed_fields",
                f"changed fields outside allowed scope: {unsupported}",
            )
        )
    if patch.original_outcome != patch.result_outcome:
        findings.append(
            StoryRoomFinding(
                "outcome_changed", "result_outcome", "subtext patch changed the locked outcome"
            )
        )
    if patch.result_outcome != _freeze(canonical_value(locked_outcome)):
        findings.append(
            StoryRoomFinding(
                "outcome_changed",
                "result_outcome",
                "result outcome does not match the locked outcome",
            )
        )
    new_entities = sorted(set(patch.result_entity_refs) - set(patch.original_entity_refs))
    if new_entities:
        findings.append(
            StoryRoomFinding(
                "new_entity", "result_entity_refs", f"patch introduces new entities: {new_entities}"
            )
        )
    return _report(findings)


__all__ = [
    "CausalBeat",
    "KnowledgeDelta",
    "SceneContractSpec",
    "SceneReaction",
    "SceneRealization",
    "StoryRoomFinding",
    "StoryRoomValidationReport",
    "SubtextPatchSpec",
    "ValidationFinding",
    "ValidationReport",
    "validate_causal_beat",
    "validate_scene_contract",
    "validate_scene_realization",
    "validate_subtext_patch",
]
