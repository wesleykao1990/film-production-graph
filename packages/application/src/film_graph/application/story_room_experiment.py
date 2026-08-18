"""Offline M04a protected-generation preflight and request planning.

The module deliberately stops at a provider-neutral request description.  It
does not import a provider SDK, read process-global credentials, write a
provenance record, or make a model call.  A caller supplies the repository
root, immutable hash pins, the resolved model identity, budgets, and (only for
an explicit execution preflight) an environment mapping from which a
credential can be checked.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Literal

import yaml
from film_graph.model_routing import ResolvedModel

ExperimentPhase = Literal["calibration", "primary"]
PreflightMode = Literal["dry_run", "execute"]

CANONICAL_CONDITIONS: tuple[str, str, str] = (
    "equal_information",
    "fixed_budget_conventional",
    "story_room",
)
REQUIRED_PINNED_GROUPS: tuple[str, ...] = (
    "protocol",
    "rules",
    "analyzer",
    "simulator",
    "anchors",
    "assignments",
    "prompts",
    "briefs",
    "operating_characteristics",
)
_PIN_GROUP_ALIASES: dict[str, tuple[str, ...]] = {
    "protocol": ("protocol",),
    "rules": ("rules", "rule"),
    "analyzer": ("analyzer", "analysis"),
    "simulator": ("simulator", "simulation"),
    "anchors": ("anchors", "anchor"),
    "assignments": ("assignments", "assignment"),
    "prompts": ("prompts", "prompt"),
    "briefs": ("briefs", "brief"),
    "operating_characteristics": (
        "operating_characteristics",
        "operating-characteristics",
    ),
}
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SENSITIVE_SETTING_RE = re.compile(
    r"(?:api[_-]?key|auth(?:orization)?|credential|password|secret|access[_-]?token|bearer)",
    re.IGNORECASE,
)
_PLACEHOLDER_WORDS = (
    "replace_before_freeze",
    "replace-before-freeze",
    "placeholder",
    "template",
    "todo",
    "tbd",
    "example",
    "not-yet-selected",
    "not_yet_selected",
    "pending-selection",
    "pre-key",
)


class ExperimentPreflightError(ValueError):
    """Raised when a request plan cannot be safely compiled."""


@dataclass(frozen=True, slots=True)
class ExperimentBudget:
    """Application-local immutable budget used by the provider-neutral plan.

    ``RunBudget`` belongs to the agent-runtime package and is intentionally
    not imported here: the application package can be installed and tested
    without that runtime.  Callers may still pass any compatible budget object
    (including an existing ``RunBudget``) to the preflight functions; values
    are copied into this local type before they enter a request descriptor.
    """

    max_model_calls: int
    max_cost_usd: Decimal
    estimated_call_cost_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if isinstance(self.max_model_calls, bool) or not isinstance(
            self.max_model_calls, int
        ):
            raise ValueError("max_model_calls must be an integer")
        if self.max_model_calls < 0:
            raise ValueError("max_model_calls must be non-negative")
        for name in ("max_cost_usd", "estimated_call_cost_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                try:
                    value = Decimal(str(value))
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise ValueError(f"{name} must be a decimal") from exc
                object.__setattr__(self, name, value)
            if not value.is_finite() or value < 0:
                raise ValueError(f"{name} must be a finite non-negative decimal")


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _canonical_json_value(value: Any) -> Any:
    """Return a JSON-compatible, deterministic representation for comparison."""

    if isinstance(value, Mapping):
        return {
            str(key): _canonical_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_canonical_json_value(item) for item in value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _settings_metadata(value: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    """Hash then discard settings so arbitrary values cannot enter reports."""

    def check_keys(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if _SENSITIVE_SETTING_RE.search(str(key)):
                    raise ValueError("model settings may not contain credential-like keys")
                check_keys(nested)
        elif isinstance(item, (list, tuple, set, frozenset)):
            for nested in item:
                check_keys(nested)

    check_keys(value)
    encoded = json.dumps(
        _canonical_json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return digest, tuple(sorted(str(key) for key in value))


def _normalise_repo_path(path: str | Path, *, label: str = "path") -> str:
    raw = _require_text(str(path), label)
    if "\x00" in raw or "\\" in raw:
        raise ValueError(f"{label} must use POSIX separators")
    posix = PurePosixPath(raw)
    normalised = posix.as_posix()
    if (
        posix.is_absolute()
        or re.match(r"^[A-Za-z]:($|/)", raw)
        or any(part in {"", ".", ".."} for part in posix.parts)
        or raw != normalised
    ):
        raise ValueError(f"{label} must be a normalized repository-relative path")
    if not normalised or normalised == ".":
        raise ValueError(f"{label} must not be empty")
    return normalised


@dataclass(frozen=True, slots=True)
class ExperimentFileRef:
    """A repository-relative file and its exact SHA-256 pin."""

    path: str
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _normalise_repo_path(self.path))
        digest = _require_text(self.sha256, "sha256")
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError("sha256 must be in the form sha256:<64 lowercase hex digits>")
        object.__setattr__(self, "sha256", digest)

    @classmethod
    def from_file(cls, repository_root: str | Path, path: str | Path) -> ExperimentFileRef:
        """Build a pin from bytes under ``repository_root``."""

        relative = _normalise_repo_path(path)
        candidate = _safe_repository_file(Path(repository_root), relative)
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        return cls(relative, f"sha256:{digest}")

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class ExperimentModelIdentity:
    """Resolved model identity plus the *name* of its credential variable."""

    alias: str
    provider: str
    model: str
    credential_env: str | None = None
    settings: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)
    settings_hash: str = field(init=False)
    setting_names: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "alias", _require_text(self.alias, "model alias"))
        object.__setattr__(self, "provider", _require_text(self.provider, "model provider"))
        object.__setattr__(self, "model", _require_text(self.model, "model name"))
        if self.credential_env is not None:
            env_name = _require_text(self.credential_env, "credential environment name")
            if not _ENV_NAME_RE.fullmatch(env_name):
                raise ValueError("credential environment name is invalid")
            object.__setattr__(self, "credential_env", env_name)
        settings_hash, setting_names = _settings_metadata(self.settings)
        object.__setattr__(self, "settings_hash", settings_hash)
        object.__setattr__(self, "setting_names", setting_names)
        object.__setattr__(self, "settings", MappingProxyType({}))

    @classmethod
    def from_resolved(
        cls,
        resolved_model: ResolvedModel,
        *,
        credential_env: str | None = None,
    ) -> ExperimentModelIdentity:
        return cls(
            alias=resolved_model.alias,
            provider=resolved_model.provider,
            model=resolved_model.model,
            credential_env=credential_env,
            settings=resolved_model.settings,
        )

    def identity_key(self) -> tuple[Any, ...]:
        return (
            self.alias,
            self.provider,
            self.model,
            self.settings_hash,
        )

    @property
    def model_family(self) -> str:
        """The application alias, which is the declared shared model family."""

        return self.alias

    @property
    def credential_env_name(self) -> str | None:
        """Credential variable name; the credential value never enters this type."""

        return self.credential_env

    def as_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "provider": self.provider,
            "model": self.model,
            "credential_env": self.credential_env,
            "settings": {
                "sha256": self.settings_hash,
                "names": list(self.setting_names),
            },
        }


def _copy_budget(value: Any, condition: str) -> ExperimentBudget:
    """Copy a local or runtime-compatible budget without importing runtime code."""

    if isinstance(value, ExperimentBudget):
        return value
    try:
        calls = value.max_model_calls
        cost = value.max_cost_usd
        estimate = getattr(value, "estimated_call_cost_usd", Decimal("0"))
    except AttributeError as exc:
        raise ValueError(
            f"budget for {condition} must expose max_model_calls and max_cost_usd"
        ) from exc
    try:
        return ExperimentBudget(calls, cost, estimate)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid budget for {condition}") from exc


@dataclass(frozen=True, slots=True)
class ConditionBudget:
    """A positive per-condition model-call and cost budget."""

    condition: str
    budget: ExperimentBudget

    def __post_init__(self) -> None:
        condition = _require_text(self.condition, "condition")
        if condition not in CANONICAL_CONDITIONS:
            raise ValueError(f"unknown experiment condition: {condition}")
        object.__setattr__(self, "condition", condition)
        budget = _copy_budget(self.budget, condition)
        object.__setattr__(self, "budget", budget)
        if budget.max_model_calls <= 0 or budget.max_cost_usd <= 0:
            raise ValueError("condition budgets must have positive calls and cost")

    def as_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "max_model_calls": self.budget.max_model_calls,
            "max_cost_usd": str(self.budget.max_cost_usd),
            "estimated_call_cost_usd": str(self.budget.estimated_call_cost_usd),
        }


@dataclass(frozen=True, slots=True)
class ProvenanceDestination:
    """A destination declaration; preflight never creates or writes it."""

    path: str
    writable: bool = True

    def __post_init__(self) -> None:
        value = _require_text(self.path, "provenance destination")
        object.__setattr__(self, "path", value)


@dataclass(frozen=True, slots=True)
class ExperimentRequestDescriptor:
    """One deterministic, hash-pinned request that a later executor may submit."""

    request_id: str
    phase: ExperimentPhase
    brief: ExperimentFileRef
    prompt: ExperimentFileRef
    condition: str
    run_index: int
    model: ExperimentModelIdentity
    budget: ExperimentBudget

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _require_text(self.request_id, "request id"))
        if self.phase not in ("calibration", "primary"):
            raise ValueError("phase must be calibration or primary")
        if self.condition not in CANONICAL_CONDITIONS:
            raise ValueError(f"unknown experiment condition: {self.condition}")
        if self.run_index <= 0:
            raise ValueError("run_index must be positive")

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "phase": self.phase,
            "brief": self.brief.as_dict(),
            "prompt": self.prompt.as_dict(),
            "condition": self.condition,
            "run_index": self.run_index,
            "model": self.model.as_dict(),
            "budget": {
                "max_model_calls": self.budget.max_model_calls,
                "max_cost_usd": str(self.budget.max_cost_usd),
                "estimated_call_cost_usd": str(self.budget.estimated_call_cost_usd),
            },
        }


@dataclass(frozen=True, slots=True)
class ExperimentRequestPlan:
    """Immutable plan produced after a successful preflight."""

    phase: ExperimentPhase
    mode: PreflightMode
    model: ExperimentModelIdentity
    protocol: ExperimentFileRef
    provenance_destination: ProvenanceDestination
    pinned_refs: Mapping[str, tuple[ExperimentFileRef, ...]]
    descriptors: tuple[ExperimentRequestDescriptor, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pinned_refs",
            MappingProxyType(
                {
                    str(group): tuple(references)
                    for group, references in sorted(self.pinned_refs.items())
                }
            ),
        )
        object.__setattr__(self, "descriptors", tuple(self.descriptors))

    @property
    def request_count(self) -> int:
        return len(self.descriptors)

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "mode": self.mode,
            "model": self.model.as_dict(),
            "protocol": self.protocol.as_dict(),
            "provenance_destination": self.provenance_destination.path,
            "pinned_refs": {
                group: [reference.as_dict() for reference in references]
                for group, references in self.pinned_refs.items()
            },
            "requests": [item.as_dict() for item in self.descriptors],
        }


@dataclass(frozen=True, slots=True)
class ExperimentPreflightReport:
    """Redacted, JSON-ready readiness result."""

    phase: ExperimentPhase
    mode: PreflightMode
    model: ExperimentModelIdentity | None
    credential_present: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    plan: ExperimentRequestPlan | None = None

    @property
    def ready(self) -> bool:
        return not self.errors and self.plan is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "mode": self.mode,
            "ready": self.ready,
            "credential_present": self.credential_present,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "plan": self.plan.as_dict() if self.plan else None,
        }


def _safe_repository_file(repository_root: Path, relative: str) -> Path:
    root = repository_root.expanduser().resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ExperimentPreflightError(f"repository path escapes root: {relative}") from exc
    if not candidate.is_file():
        raise ExperimentPreflightError(f"pinned file is missing: {relative}")
    return candidate


def verify_file_ref(repository_root: str | Path, reference: ExperimentFileRef) -> None:
    """Verify one exact repository-relative file pin without mutating the tree."""

    candidate = _safe_repository_file(Path(repository_root), reference.path)
    actual = f"sha256:{hashlib.sha256(candidate.read_bytes()).hexdigest()}"
    if actual != reference.sha256:
        raise ExperimentPreflightError(f"hash mismatch for pinned file: {reference.path}")


def _coerce_file_ref(value: Any, label: str) -> ExperimentFileRef:
    if isinstance(value, ExperimentFileRef):
        return value
    if isinstance(value, Mapping):
        path = value.get("path")
        digest = value.get("sha256", value.get("hash"))
        if not isinstance(path, str) or not isinstance(digest, str):
            raise ValueError(f"{label} must include string path and sha256")
        return ExperimentFileRef(path, digest)
    raise ValueError(f"{label} must contain ExperimentFileRef values")


def _normalise_pins(
    pinned_refs: Mapping[str, Any] | None,
    protocol_ref: ExperimentFileRef | None,
) -> dict[str, tuple[ExperimentFileRef, ...]]:
    result: dict[str, tuple[ExperimentFileRef, ...]] = {}
    for key, raw in (pinned_refs or {}).items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("pinned reference group names must be non-empty strings")
        key = key.strip()
        values: tuple[Any, ...]
        if isinstance(raw, ExperimentFileRef):
            values = (raw,)
        elif isinstance(raw, Mapping):
            # A single file reference is a mapping with ``path`` and a hash;
            # keyed groups (for example ``prompts: {condition: ref}``) are
            # also convenient for callers and are normalized to their values.
            if "path" in raw and ("sha256" in raw or "hash" in raw):
                values = (raw,)
            else:
                values = tuple(raw.values())
        elif isinstance(raw, (str, bytes)):
            values = (raw,)
        elif isinstance(raw, Sequence):
            values = tuple(raw)
        else:
            raise ValueError(f"pinned reference group {key!r} is invalid")
        result[key] = tuple(_coerce_file_ref(value, key) for value in values)
    if protocol_ref is not None:
        existing = result.get("protocol")
        if existing and existing != (protocol_ref,):
            raise ValueError("protocol_ref conflicts with pinned_refs['protocol']")
        result["protocol"] = (protocol_ref,)
    return result


def _normalise_model(
    model: ResolvedModel | ExperimentModelIdentity,
    credential_env: str | None,
) -> ExperimentModelIdentity:
    if isinstance(model, ExperimentModelIdentity):
        if credential_env is None or model.credential_env == credential_env:
            return model
        raise ValueError("credential environment names conflict")
    if isinstance(model, ResolvedModel):
        return ExperimentModelIdentity.from_resolved(model, credential_env=credential_env)
    raise ValueError("resolved_model must be a ResolvedModel or ExperimentModelIdentity")


def _normalise_budget(value: Any, condition: str) -> ConditionBudget:
    if isinstance(value, ConditionBudget):
        if value.condition != condition:
            raise ValueError(f"budget condition mismatch for {condition}")
        return value
    if isinstance(value, ExperimentBudget) or all(
        hasattr(value, attribute)
        for attribute in ("max_model_calls", "max_cost_usd")
    ):
        return ConditionBudget(condition, _copy_budget(value, condition))
    if not isinstance(value, Mapping):
        raise ValueError(f"budget for {condition} must be a budget object or mapping")
    try:
        calls = value["max_model_calls"]
        cost = Decimal(str(value["max_cost_usd"]))
        estimate = Decimal(str(value.get("estimated_call_cost_usd", "0")))
        budget = ExperimentBudget(
            max_model_calls=calls,
            max_cost_usd=cost,
            estimated_call_cost_usd=estimate,
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(f"invalid budget for {condition}") from exc
    return ConditionBudget(condition, budget)


def _normalise_budgets(budgets: Mapping[str, Any]) -> dict[str, ConditionBudget]:
    if not isinstance(budgets, Mapping):
        raise ValueError("condition_budgets must be a mapping")
    actual = {str(key): value for key, value in budgets.items()}
    missing = [item for item in CANONICAL_CONDITIONS if item not in actual]
    extra = [item for item in actual if item not in CANONICAL_CONDITIONS]
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append("missing budgets: " + ", ".join(missing))
        if extra:
            parts.append("unknown budgets: " + ", ".join(sorted(extra)))
        raise ValueError("; ".join(parts))
    return {
        condition: _normalise_budget(actual[condition], condition)
        for condition in CANONICAL_CONDITIONS
    }


def _protocol_conditions(protocol: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw_conditions = protocol.get("conditions")
    if not isinstance(raw_conditions, Sequence) or isinstance(raw_conditions, (str, bytes)):
        raise ValueError("protocol.conditions must be a sequence")
    conditions: dict[str, Mapping[str, Any]] = {}
    for raw in raw_conditions:
        if not isinstance(raw, Mapping):
            raise ValueError("each protocol condition must be a mapping")
        condition = _require_text(raw.get("id"), "condition id")
        if condition in conditions:
            raise ValueError(f"duplicate protocol condition: {condition}")
        conditions[condition] = raw
    missing = [item for item in CANONICAL_CONDITIONS if item not in conditions]
    extra = [item for item in conditions if item not in CANONICAL_CONDITIONS]
    if missing or extra:
        detail = []
        if missing:
            detail.append("missing conditions: " + ", ".join(missing))
        if extra:
            detail.append("unknown conditions: " + ", ".join(sorted(extra)))
        raise ValueError("; ".join(detail))
    return conditions


def _resolve_reference_path(raw: Any, *, protocol_path: str) -> str:
    value = _require_text(raw, "protocol reference path")
    if "\\" in value or Path(value).is_absolute():
        raise ValueError("protocol reference paths must be relative POSIX paths")
    base = PurePosixPath(protocol_path).parent
    joined = PurePosixPath(base, value)
    parts: list[str] = []
    for part in joined.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError("protocol reference path escapes repository root")
            parts.pop()
        else:
            parts.append(part)
    if not parts:
        raise ValueError("protocol reference path is empty")
    return PurePosixPath(*parts).as_posix()


def _find_pin(
    refs: Mapping[str, tuple[ExperimentFileRef, ...]], group: str, path: str
) -> ExperimentFileRef:
    for reference in _pin_group(refs, group):
        if reference.path == path:
            return reference
    raise ExperimentPreflightError(f"missing {group} pin for referenced file: {path}")


def _pin_group(
    refs: Mapping[str, tuple[ExperimentFileRef, ...]], group: str
) -> tuple[ExperimentFileRef, ...]:
    """Return one canonical pin group, accepting singular fixture spellings."""

    for name in _PIN_GROUP_ALIASES.get(group, (group,)):
        values = refs.get(name, ())
        if values:
            return values
    return ()


def _validate_pins(
    repository_root: Path,
    refs: Mapping[str, tuple[ExperimentFileRef, ...]],
    *,
    required_groups: Sequence[str] = (),
) -> list[str]:
    errors: list[str] = []
    for group in required_groups:
        if not _pin_group(refs, group):
            errors.append(f"missing required pinned reference group: {group}")
    for _group, values in refs.items():
        for reference in values:
            try:
                verify_file_ref(repository_root, reference)
            except (ExperimentPreflightError, OSError) as exc:
                errors.append(str(exc))
    return errors


def _load_pinned_protocol(
    repository_root: Path,
    refs: Mapping[str, tuple[ExperimentFileRef, ...]],
) -> tuple[Mapping[str, Any] | None, list[str]]:
    """Load the exact pinned YAML document so callers cannot substitute a mapping."""

    protocol_refs = _pin_group(refs, "protocol")
    if len(protocol_refs) != 1:
        return None, ["exactly one protocol pin is required"]
    try:
        path = _safe_repository_file(repository_root, protocol_refs[0].path)
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError, ExperimentPreflightError) as exc:
        return None, [f"unable to load pinned protocol: {type(exc).__name__}"]
    if not isinstance(loaded, Mapping):
        return None, ["pinned protocol must contain a mapping"]
    return loaded, []


def _validate_protocol_reference_pins(
    protocol: Mapping[str, Any],
    protocol_path: str,
    refs: Mapping[str, tuple[ExperimentFileRef, ...]],
    *,
    phase: ExperimentPhase,
    require_freeze_artifacts: bool,
) -> list[str]:
    """Bind protocol-declared paths and fixed rule sources to their pin groups."""

    errors: list[str] = []
    try:
        conditions = _protocol_conditions(protocol)
        for condition in CANONICAL_CONDITIONS:
            path = _resolve_reference_path(
                conditions[condition].get("prompt_path"), protocol_path=protocol_path
            )
            _find_pin(refs, "prompts", path)
        calibration = _resolve_reference_path(
            protocol.get("calibration_brief"), protocol_path=protocol_path
        )
        _find_pin(refs, "briefs", calibration)
        if phase == "primary":
            primary = protocol.get("primary_briefs")
            if not isinstance(primary, Sequence) or isinstance(primary, (str, bytes)):
                raise ValueError("protocol.primary_briefs must be a sequence")
            for raw in primary:
                _find_pin(
                    refs,
                    "briefs",
                    _resolve_reference_path(raw, protocol_path=protocol_path),
                )
        if require_freeze_artifacts:
            presentation = protocol.get("presentation")
            if not isinstance(presentation, Mapping):
                raise ValueError("protocol.presentation must be a mapping")
            assignment = _resolve_reference_path(
                presentation.get("assignment_plan"), protocol_path=protocol_path
            )
            _find_pin(refs, "assignments", assignment)
            instrument = protocol.get("instrument_validity")
            positive = (
                instrument.get("positive_control")
                if isinstance(instrument, Mapping)
                else None
            )
            if not isinstance(positive, Mapping):
                raise ValueError("protocol positive-control configuration is missing")
            anchor = _resolve_reference_path(
                positive.get("anchor_manifest"), protocol_path=protocol_path
            )
            _find_pin(refs, "anchors", anchor)
            operating = protocol.get("operating_characteristics")
            if not isinstance(operating, Mapping):
                raise ValueError("protocol operating-characteristics configuration is missing")
            simulator = _resolve_reference_path(
                operating.get("script_path"), protocol_path=protocol_path
            )
            _find_pin(refs, "simulator", simulator)
            output = _resolve_reference_path(
                operating.get("planned_output_path"), protocol_path=protocol_path
            )
            _find_pin(refs, "operating_characteristics", output)
            _find_pin(refs, "rules", "scripts/m4_rules.py")
            _find_pin(refs, "analyzer", "scripts/analyze_m4.py")
    except (ExperimentPreflightError, ValueError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return not text or any(word in text for word in _PLACEHOLDER_WORDS)
    return False


def _positive_decimal(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return number.is_finite() and number > 0


def _real_text(value: Any) -> bool:
    return isinstance(value, str) and not _is_placeholder(value)


def _validate_frozen_protocol(
    protocol: Mapping[str, Any],
    refs: Mapping[str, tuple[ExperimentFileRef, ...]],
    budgets: Mapping[str, ConditionBudget],
) -> list[str]:
    errors: list[str] = []
    if protocol.get("status") != "frozen":
        errors.append("primary execution requires protocol status frozen")
    if not _real_text(protocol.get("frozen_at")):
        errors.append("primary execution requires frozen_at")

    budget_freeze = protocol.get("budget_freeze")
    if not isinstance(budget_freeze, Mapping):
        errors.append("primary execution requires budget_freeze")
    else:
        cap = budget_freeze.get("projected_story_room_cap_usd_per_sample")
        if not _positive_decimal(cap):
            errors.append("primary execution requires a positive frozen story-room cap")
        price_ref = budget_freeze.get("provider_price_snapshot_ref")
        if not _real_text(price_ref):
            errors.append("primary execution requires a non-placeholder provider price snapshot")
        multiplier = budget_freeze.get("fixed_budget_conventional_multiplier")
        if not _positive_decimal(multiplier) or Decimal(str(multiplier)) != Decimal("1.5"):
            errors.append("primary execution requires the frozen conventional multiplier 1.5")
        if _positive_decimal(cap) and Decimal(str(multiplier or 0)) == Decimal("1.5"):
            story_cap = Decimal(str(cap))
            conventional_cap = story_cap * Decimal(str(multiplier))
            if budgets.get("story_room") and (
                budgets["story_room"].budget.max_cost_usd != story_cap
            ):
                errors.append("story-room execution budget does not match the frozen cap")
            if budgets.get("fixed_budget_conventional") and (
                budgets["fixed_budget_conventional"].budget.max_cost_usd
                != conventional_cap
            ):
                errors.append("conventional execution budget does not match the frozen cap")

        frozen_budgets = budget_freeze.get("condition_budgets")
        if not isinstance(frozen_budgets, Mapping):
            errors.append("primary execution requires frozen per-condition budgets")
        else:
            for condition in CANONICAL_CONDITIONS:
                raw_budget = frozen_budgets.get(condition)
                if raw_budget is None:
                    errors.append(f"primary execution requires frozen budget: {condition}")
                    continue
                try:
                    frozen = _normalise_budget(raw_budget, condition)
                except (TypeError, ValueError):
                    errors.append(
                        f"primary execution requires a positive frozen budget: {condition}"
                    )
                    continue
                declared = budgets.get(condition)
                if declared is None or frozen.budget != declared.budget:
                    errors.append(
                        f"execution budget does not match frozen budget: {condition}"
                    )

    operating = protocol.get("operating_characteristics")
    if not isinstance(operating, Mapping):
        errors.append("primary execution requires operating_characteristics")
    else:
        for name in ("reviewed_by", "reviewed_at", "output_hash"):
            if not _real_text(operating.get(name)):
                errors.append(
                    f"primary execution requires reviewed operating-characteristics {name}"
                )
        output_hash = operating.get("output_hash")
        if not _is_placeholder(output_hash) and (
            not isinstance(output_hash, str) or not _SHA256_RE.fullmatch(output_hash)
        ):
            errors.append("operating_characteristics.output_hash must be a sha256 digest")
        trials = operating.get("trials_minimum", 0)
        if isinstance(trials, bool) or not isinstance(trials, int):
            errors.append("operating_characteristics.trials_minimum must be an integer")
        elif trials <= 0:
            errors.append("operating_characteristics.trials_minimum must be positive")
        if operating.get("sensitivity_required") is not True:
            errors.append("operating_characteristics.sensitivity_required must be true")
        if operating.get("mandatory_reliability_mode") != "simulate":
            errors.append("operating_characteristics must use simulate reliability")
        calibration_inputs = operating.get("calibration_inputs")
        if not isinstance(calibration_inputs, Mapping) or any(
            _is_placeholder(calibration_inputs.get(name))
            for name in (
                "tie_rate",
                "rater_sd_logit",
                "brief_sd_logit",
                "anchor_true_preference",
                "anchor_rater_sd_logit",
            )
        ):
            errors.append(
                "primary execution requires reviewed operating-characteristics calibration inputs"
            )
    operating_refs = _pin_group(refs, "operating_characteristics")
    if isinstance(operating, Mapping):
        expected = operating.get("output_hash")
        if len(operating_refs) != 1:
            errors.append("primary execution requires exactly one operating-characteristics pin")
        elif isinstance(expected, str) and operating_refs[0].sha256 != expected:
            errors.append("operating-characteristics hash does not match its pinned file")
    return errors


def _validate_destination(destination: ProvenanceDestination, *, execute: bool) -> list[str]:
    if not execute:
        return []
    if not destination.writable:
        return ["provenance destination is not declared writable"]
    path = Path(destination.path).expanduser()
    parent = path if path.is_dir() else path.parent
    if not parent.exists() or not parent.is_dir():
        return ["provenance destination parent does not exist"]
    if not os.access(parent, os.W_OK):
        return ["provenance destination parent is not writable"]
    return []


def _normalise_condition_models(
    models: Mapping[str, Any] | None,
    credential_env: str | None,
) -> dict[str, ExperimentModelIdentity]:
    if models is None:
        return {}
    if not isinstance(models, Mapping):
        raise ValueError("condition_models must be a mapping")
    result: dict[str, ExperimentModelIdentity] = {}
    for condition, model in models.items():
        if condition not in CANONICAL_CONDITIONS:
            raise ValueError(f"unknown condition model: {condition}")
        result[condition] = _normalise_model(model, credential_env)
    return result


def _build_descriptors(
    *,
    phase: ExperimentPhase,
    protocol: Mapping[str, Any],
    protocol_path: str,
    refs: Mapping[str, tuple[ExperimentFileRef, ...]],
    model: ExperimentModelIdentity,
    budgets: Mapping[str, ConditionBudget],
) -> tuple[ExperimentRequestDescriptor, ...]:
    conditions = _protocol_conditions(protocol)
    prompt_refs: dict[str, ExperimentFileRef] = {}
    for condition in CANONICAL_CONDITIONS:
        prompt_path = _resolve_reference_path(
            conditions[condition].get("prompt_path"), protocol_path=protocol_path
        )
        prompt_refs[condition] = _find_pin(refs, "prompts", prompt_path)

    if phase == "calibration":
        raw_brief = protocol.get("calibration_brief")
        brief_path = _resolve_reference_path(raw_brief, protocol_path=protocol_path)
        brief = _find_pin(refs, "briefs", brief_path)
        return tuple(
            ExperimentRequestDescriptor(
                request_id=f"calibration-{condition}",
                phase=phase,
                brief=brief,
                prompt=prompt_refs[condition],
                condition=condition,
                run_index=1,
                model=model,
                budget=budgets[condition].budget,
            )
            for condition in CANONICAL_CONDITIONS
        )

    raw_briefs = protocol.get("primary_briefs")
    if not isinstance(raw_briefs, Sequence) or isinstance(raw_briefs, (str, bytes)):
        raise ValueError("protocol.primary_briefs must be a sequence")
    brief_refs = tuple(
        _find_pin(refs, "briefs", _resolve_reference_path(item, protocol_path=protocol_path))
        for item in raw_briefs
    )
    if len(brief_refs) != 3:
        raise ValueError("primary execution requires exactly three primary briefs")
    if len({item.path for item in brief_refs}) != 3:
        raise ValueError("primary execution requires three distinct primary briefs")
    runs = protocol.get("runs_per_condition", 3)
    if isinstance(runs, bool) or not isinstance(runs, int) or runs != 3:
        raise ValueError("primary execution requires exactly three runs per condition")
    return tuple(
        ExperimentRequestDescriptor(
                request_id=(
                    f"primary-{brief.path.rsplit('/', 1)[-1].rsplit('.', 1)[0]}"
                    f"-run-{run}-{condition}"
                ),
            phase=phase,
            brief=brief,
            prompt=prompt_refs[condition],
            condition=condition,
            run_index=run,
            model=model,
            budget=budgets[condition].budget,
        )
        for brief in brief_refs
        for run in range(1, 4)
        for condition in CANONICAL_CONDITIONS
    )


def _compile(
    *,
    repository_root: str | Path,
    protocol: Mapping[str, Any],
    phase: ExperimentPhase,
    mode: PreflightMode,
    resolved_model: ResolvedModel | ExperimentModelIdentity,
    condition_budgets: Mapping[str, Any],
    protocol_ref: ExperimentFileRef | None,
    pinned_refs: Mapping[str, Any] | None,
    credential_env: str | None,
    environment: Mapping[str, str] | None,
    provenance_destination: ProvenanceDestination | str | Path | None,
    condition_models: Mapping[str, Any] | None,
    protocol_path: str | None,
) -> ExperimentPreflightReport:
    errors: list[str] = []
    root = Path(repository_root)
    model: ExperimentModelIdentity | None = None
    credential_present = False
    try:
        model = _normalise_model(resolved_model, credential_env)
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))

    try:
        budgets = _normalise_budgets(condition_budgets)
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
        budgets = {}

    try:
        refs = _normalise_pins(pinned_refs, protocol_ref)
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
        refs = {}

    required_groups: Sequence[str]
    if mode == "execute" and phase == "primary":
        required_groups = REQUIRED_PINNED_GROUPS
    else:
        required_groups = ("protocol", "prompts", "briefs")
    errors.extend(_validate_pins(root, refs, required_groups=required_groups))
    if not isinstance(protocol, Mapping):
        errors.append("protocol must be a mapping")
        protocol_mapping: Mapping[str, Any] = {}
    else:
        protocol_mapping = protocol

    pinned_protocol, protocol_load_errors = _load_pinned_protocol(root, refs)
    errors.extend(protocol_load_errors)
    if pinned_protocol is not None and (
        _canonical_json_value(pinned_protocol) != _canonical_json_value(protocol_mapping)
    ):
        errors.append("supplied protocol mapping does not match the pinned protocol file")
    protocol_refs = _pin_group(refs, "protocol")
    if protocol_path is not None and len(protocol_refs) == 1:
        try:
            declared_protocol_path = _normalise_repo_path(
                protocol_path, label="protocol_path"
            )
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if declared_protocol_path != protocol_refs[0].path:
                errors.append("protocol_path must match the pinned protocol path")
    selected_protocol_path = protocol_path or (
        protocol_refs[0].path if len(protocol_refs) == 1 else ""
    )
    if selected_protocol_path:
        errors.extend(
            _validate_protocol_reference_pins(
                protocol_mapping,
                selected_protocol_path,
                refs,
                phase=phase,
                require_freeze_artifacts=mode == "execute" and phase == "primary",
            )
        )
    if model is not None:
        try:
            condition_identity = _normalise_condition_models(condition_models, credential_env)
            for condition, identity in condition_identity.items():
                if identity.identity_key() != model.identity_key():
                    errors.append(f"model identity mismatch for condition: {condition}")
        except (ValueError, TypeError) as exc:
            errors.append(str(exc))

    if mode == "execute" and model is not None:
        for label, value in (
            ("model alias", model.alias),
            ("model provider", model.provider),
            ("model name", model.model),
        ):
            if _is_placeholder(value):
                errors.append(f"protected execution requires a non-placeholder {label}")

    if provenance_destination is None:
        destination = ProvenanceDestination("provenance/experiment.json")
    elif isinstance(provenance_destination, ProvenanceDestination):
        destination = provenance_destination
    else:
        destination = ProvenanceDestination(str(provenance_destination))
    errors.extend(_validate_destination(destination, execute=mode == "execute"))

    if mode == "execute" and phase == "primary":
        errors.extend(_validate_frozen_protocol(protocol_mapping, refs, budgets))
    elif mode == "execute" and protocol_mapping.get("status") not in {
        "draft",
        "calibrated",
        "frozen",
    }:
        errors.append("calibration execution requires a draft, calibrated, or frozen protocol")

    # Validate every non-secret precondition first.  A malformed/draft
    # protocol must not cause the caller's credential mapping to be touched.
    # This is also what keeps the boundary useful in ordinary no-key tests.
    if mode == "execute" and not errors:
        if model is None or not model.credential_env:
            errors.append("protected execution requires a credential environment name")
        elif environment is None:
            errors.append(f"credential environment mapping is required for {model.credential_env}")
        else:
            # This is the only place in this module that reads the caller's
            # mapping, and only after execute mode has been explicitly chosen
            # and every static check has passed.
            credential = environment.get(model.credential_env)
            credential_present = isinstance(credential, str) and bool(credential.strip())
            if not credential_present:
                errors.append(
                    f"credential is missing for environment variable {model.credential_env}"
                )

    if model is None or not budgets or errors:
        return ExperimentPreflightReport(
            phase=phase,
            mode=mode,
            model=model,
            credential_present=credential_present,
            errors=tuple(dict.fromkeys(errors)),
        )

    try:
        conditions = _protocol_conditions(protocol_mapping)
        del conditions  # validation above is intentionally separate from path resolution
        selected_protocol = refs.get("protocol", ())
        if not selected_protocol:
            raise ExperimentPreflightError("missing protocol pin")
        selected_protocol_ref = selected_protocol[0]
        base_path = protocol_path or selected_protocol_ref.path
        descriptors = _build_descriptors(
            phase=phase,
            protocol=protocol_mapping,
            protocol_path=base_path,
            refs=refs,
            model=model,
            budgets=budgets,
        )
        expected = 3 if phase == "calibration" else 27
        if len(descriptors) != expected:
            raise ExperimentPreflightError(
                f"unexpected request descriptor count: {len(descriptors)}"
            )
        plan = ExperimentRequestPlan(
            phase=phase,
            mode=mode,
            model=model,
            protocol=selected_protocol_ref,
            provenance_destination=destination,
            pinned_refs=refs,
            descriptors=descriptors,
        )
    except (ExperimentPreflightError, ValueError, TypeError, KeyError) as exc:
        errors.append(str(exc))
        plan = None
    return ExperimentPreflightReport(
        phase=phase,
        mode=mode,
        model=model,
        credential_present=credential_present,
        errors=tuple(dict.fromkeys(errors)),
        plan=plan if not errors else None,
    )


def preflight_experiment(
    *,
    repository_root: str | Path,
    protocol: Mapping[str, Any],
    phase: ExperimentPhase,
    resolved_model: ResolvedModel | ExperimentModelIdentity,
    condition_budgets: Mapping[str, Any],
    mode: PreflightMode = "dry_run",
    protocol_ref: ExperimentFileRef | None = None,
    pinned_refs: Mapping[str, Any] | None = None,
    credential_env: str | None = None,
    environment: Mapping[str, str] | None = None,
    provenance_destination: ProvenanceDestination | str | Path | None = None,
    condition_models: Mapping[str, Any] | None = None,
    protocol_path: str | None = None,
    raise_on_error: bool = False,
) -> ExperimentPreflightReport:
    """Run static or protected preflight and return a redacted report.

    ``mode='dry_run'`` never reads ``environment``.  Set ``mode='execute'``
    to require a caller-supplied, non-empty credential and the stronger
    protected-generation checks.  ``raise_on_error`` is useful at CLI
    boundaries; the default keeps this function convenient for diagnostics.
    """

    if phase not in ("calibration", "primary"):
        raise ValueError("phase must be calibration or primary")
    if mode not in ("dry_run", "execute"):
        raise ValueError("mode must be dry_run or execute")
    report = _compile(
        repository_root=repository_root,
        protocol=protocol,
        phase=phase,
        mode=mode,
        resolved_model=resolved_model,
        condition_budgets=condition_budgets,
        protocol_ref=protocol_ref,
        pinned_refs=pinned_refs,
        credential_env=credential_env,
        environment=environment,
        provenance_destination=provenance_destination,
        condition_models=condition_models,
        protocol_path=protocol_path,
    )
    if raise_on_error and not report.ready:
        raise ExperimentPreflightError("; ".join(report.errors))
    return report


def compile_request_plan(
    *,
    repository_root: str | Path,
    protocol: Mapping[str, Any],
    phase: ExperimentPhase,
    resolved_model: ResolvedModel | ExperimentModelIdentity,
    condition_budgets: Mapping[str, Any],
    mode: PreflightMode = "dry_run",
    protocol_ref: ExperimentFileRef | None = None,
    pinned_refs: Mapping[str, Any] | None = None,
    credential_env: str | None = None,
    environment: Mapping[str, str] | None = None,
    provenance_destination: ProvenanceDestination | str | Path | None = None,
    condition_models: Mapping[str, Any] | None = None,
    protocol_path: str | None = None,
) -> ExperimentRequestPlan:
    """Compile an immutable request plan or raise a redacted preflight error."""

    report = preflight_experiment(
        repository_root=repository_root,
        protocol=protocol,
        phase=phase,
        resolved_model=resolved_model,
        condition_budgets=condition_budgets,
        mode=mode,
        protocol_ref=protocol_ref,
        pinned_refs=pinned_refs,
        credential_env=credential_env,
        environment=environment,
        provenance_destination=provenance_destination,
        condition_models=condition_models,
        protocol_path=protocol_path,
    )
    if not report.ready or report.plan is None:
        raise ExperimentPreflightError("; ".join(report.errors))
    return report.plan


__all__ = [
    "CANONICAL_CONDITIONS",
    "ConditionBudget",
    "ExperimentBudget",
    "ExperimentFileRef",
    "ExperimentModelIdentity",
    "ExperimentPhase",
    "ExperimentPreflightError",
    "ExperimentPreflightReport",
    "ExperimentRequestDescriptor",
    "ExperimentRequestPlan",
    "PreflightMode",
    "ProvenanceDestination",
    "compile_request_plan",
    "preflight_experiment",
    "verify_file_ref",
]
