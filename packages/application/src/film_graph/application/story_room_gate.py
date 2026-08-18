"""Pure bridge from Story Room validation records to the M04a gate manifest.

The Story Room validators live in :mod:`film_graph.domain.story_room`.  This
module deliberately does not run them or make a product decision.  It only
checks that a complete, already-validated sample set can be represented in
the authoritative M04 run-manifest shape, and creates a separate opaque
projection for raters.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from film_graph.domain import StoryRoomValidationReport

from .errors import ValidationError

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_MODES = frozenset({"standard_seven", "standard_six", "standard_five", "degraded_three"})
_CONDITIONS = (
    "equal_information",
    "fixed_budget_conventional",
    "story_room",
)
_DIMENSIONS = ("specificity", "character_voice", "causal_progression")
_DIMENSION_COUNTS = Counter(_DIMENSIONS)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{label} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _hash(value: Any, label: str) -> str:
    result = _nonempty(value, label)
    if not _HASH_RE.fullmatch(result):
        raise ValidationError(f"{label} must be a lowercase sha256 hash")
    return result


def _finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be a non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValidationError(f"{label} must be a non-negative finite number")
    return result


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _freeze(item) for key, item in value.items()}
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _error_count(report: StoryRoomValidationReport) -> int:
    return sum(1 for finding in report.findings if finding.severity == "error")


@dataclass(frozen=True, slots=True)
class GateSampleRecord:
    """One complete scored sample before manifest projection.

    ``hard_violation_count`` is intentionally not a field.  It is derived from
    the supplied deterministic validation report by :func:`build_run_manifest`.
    """

    sample_id: str
    brief_id: str
    run_index: int
    condition: str
    valid: bool
    validation_report: StoryRoomValidationReport
    target_scene_position: int | None = None
    target_scene_id: str | None = None
    target_scene_hash: str | None = None
    invalid_reason: str | None = None
    cost_usd: float = 0.0
    latency_seconds: float = 0.0
    triplet_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sample_id", _nonempty(self.sample_id, "sample_id"))
        object.__setattr__(self, "brief_id", _nonempty(self.brief_id, "brief_id"))
        if isinstance(self.run_index, bool) or not isinstance(self.run_index, int):
            raise ValidationError("run_index must be an integer")
        if self.run_index not in {1, 2, 3}:
            raise ValidationError("run_index must be between 1 and 3")
        if self.condition not in _CONDITIONS:
            raise ValidationError(f"unsupported condition: {self.condition!r}")
        if not isinstance(self.valid, bool):
            raise ValidationError("valid must be a boolean")
        if not isinstance(self.validation_report, StoryRoomValidationReport):
            raise ValidationError("validation_report must be a StoryRoomValidationReport instance")
        if self.valid and not self.validation_report.valid:
            raise ValidationError("valid samples require a valid StoryRoomValidationReport")
        if not self.valid and self.invalid_reason is None:
            raise ValidationError("invalid samples require invalid_reason")
        if self.target_scene_position is not None and (
            isinstance(self.target_scene_position, bool)
            or not isinstance(self.target_scene_position, int)
            or self.target_scene_position < 1
        ):
            raise ValidationError("target_scene_position must be a positive integer or null")
        if self.target_scene_id is not None:
            object.__setattr__(
                self,
                "target_scene_id",
                _nonempty(self.target_scene_id, "target_scene_id"),
            )
        if self.target_scene_hash is not None:
            object.__setattr__(
                self,
                "target_scene_hash",
                _hash(self.target_scene_hash, "target_scene_hash"),
            )
        if self.invalid_reason is not None:
            object.__setattr__(
                self,
                "invalid_reason",
                _nonempty(self.invalid_reason, "invalid_reason"),
            )
        object.__setattr__(self, "cost_usd", _finite_nonnegative(self.cost_usd, "cost_usd"))
        object.__setattr__(
            self, "latency_seconds", _finite_nonnegative(self.latency_seconds, "latency_seconds")
        )
        triplet = self.triplet_id.strip() if isinstance(self.triplet_id, str) else ""
        object.__setattr__(
            self,
            "triplet_id",
            triplet or f"{self.brief_id}-run-{self.run_index}",
        )

    @property
    def scene_id(self) -> str | None:
        """Alias used by callers that call the target scene simply ``scene``."""

        return self.target_scene_id

    @property
    def scene_hash(self) -> str | None:
        return self.target_scene_hash

    @property
    def validator_report(self) -> StoryRoomValidationReport:
        return self.validation_report


@dataclass(frozen=True, slots=True)
class AnchorTaskRecord:
    """Confidential admin-side forced-choice anchor role mapping."""

    anchor_id: str
    dimensions: tuple[str, ...]
    left_sample_id: str
    right_sample_id: str
    intact_sample_id: str
    degraded_sample_id: str
    response_mode: str = "forced_choice"

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchor_id", _nonempty(self.anchor_id, "anchor_id"))
        dimensions = tuple(_nonempty(item, "anchor dimension") for item in self.dimensions)
        if not dimensions or len(dimensions) > 2 or len(set(dimensions)) != len(dimensions):
            raise ValidationError("anchor dimensions must contain one or two unique values")
        if any(item not in _DIMENSIONS for item in dimensions):
            raise ValidationError("anchor dimensions contain an unsupported dimension")
        object.__setattr__(self, "dimensions", dimensions)
        for field_name in (
            "left_sample_id",
            "right_sample_id",
            "intact_sample_id",
            "degraded_sample_id",
        ):
            object.__setattr__(self, field_name, _nonempty(getattr(self, field_name), field_name))
        if self.left_sample_id == self.right_sample_id:
            raise ValidationError("anchor left and right samples must differ")
        if {self.left_sample_id, self.right_sample_id} != {
            self.intact_sample_id,
            self.degraded_sample_id,
        }:
            raise ValidationError("anchor left/right mapping must match intact/degraded roles")
        if self.response_mode != "forced_choice":
            raise ValidationError("anchor response_mode must be forced_choice")


def _coerce_sample(value: GateSampleRecord | Mapping[str, Any]) -> GateSampleRecord:
    if isinstance(value, GateSampleRecord):
        return value
    raw = _mapping(value, "sample record")
    if "validation_report" not in raw:
        raw["validation_report"] = raw.get("validator_report", raw.get("report"))
    if "target_scene_id" not in raw and "scene_id" in raw:
        raw["target_scene_id"] = raw["scene_id"]
    if "target_scene_hash" not in raw and "scene_hash" in raw:
        raw["target_scene_hash"] = raw["scene_hash"]
    allowed = {name for name in GateSampleRecord.__dataclass_fields__}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValidationError(f"sample record has unsupported fields: {unknown}")
    return GateSampleRecord(**raw)


def _coerce_anchor(value: AnchorTaskRecord | Mapping[str, Any]) -> AnchorTaskRecord:
    if isinstance(value, AnchorTaskRecord):
        return value
    raw = _mapping(value, "anchor task")
    allowed = {name for name in AnchorTaskRecord.__dataclass_fields__}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValidationError(f"anchor task has unsupported fields: {unknown}")
    return AnchorTaskRecord(**raw)


def _validate_anchors(
    values: Iterable[AnchorTaskRecord | Mapping[str, Any]],
) -> tuple[AnchorTaskRecord, ...]:
    anchors = tuple(_coerce_anchor(value) for value in values)
    if len(anchors) != 2:
        raise ValidationError("exactly two anchor tasks are required")
    if len({item.anchor_id for item in anchors}) != len(anchors):
        raise ValidationError("anchor IDs must be unique")
    covered = Counter(dimension for item in anchors for dimension in item.dimensions)
    if covered != _DIMENSION_COUNTS:
        raise ValidationError("anchor dimensions must cover each primary dimension exactly once")
    return tuple(sorted(anchors, key=lambda item: item.anchor_id))


def _sample_manifest(record: GateSampleRecord) -> dict[str, Any]:
    errors = _error_count(record.validation_report)
    if record.valid:
        if record.target_scene_position != 2:
            raise ValidationError("valid samples must target scene position 2")
        if record.target_scene_id is None or record.target_scene_hash is None:
            raise ValidationError("valid samples require target scene ID and hash")
        if errors:
            raise ValidationError("valid samples may not contain hard validation errors")
        if record.invalid_reason is not None:
            raise ValidationError("valid samples must not have invalid_reason")
    elif record.invalid_reason is None:
        raise ValidationError("invalid samples require invalid_reason")
    return {
        "sample_id": record.sample_id,
        "condition": record.condition,
        "valid": record.valid,
        "invalid_reason": record.invalid_reason,
        "target_scene_id": record.target_scene_id,
        "target_scene_hash": record.target_scene_hash,
        "hard_violation_count": errors,
        "cost_usd": record.cost_usd,
        "latency_seconds": record.latency_seconds,
    }


def build_run_manifest(
    samples: Iterable[GateSampleRecord | Mapping[str, Any]],
    anchor_tasks: Iterable[AnchorTaskRecord | Mapping[str, Any]] | None = None,
    *,
    protocol_hash: str,
    anchor_manifest_hash: str,
    run_mode: str,
    run_manifest_version: str = "2.4.0",
) -> dict[str, Any]:
    """Build the authoritative admin manifest from all 27 scored samples.

    Input order has no meaning.  Every record is validated and included; the
    output is sorted by brief, run, then the canonical condition order.
    """

    protocol = _hash(protocol_hash, "protocol_hash")
    anchor_hash = _hash(anchor_manifest_hash, "anchor_manifest_hash")
    mode = _nonempty(run_mode, "run_mode")
    if mode not in _RUN_MODES:
        raise ValidationError(f"unsupported run_mode: {mode}")
    version = _nonempty(run_manifest_version, "run_manifest_version")
    if anchor_tasks is None:
        raise ValidationError("anchor_tasks are required")
    anchors = _validate_anchors(anchor_tasks)
    records = tuple(_coerce_sample(value) for value in samples)
    if len(records) != 27:
        raise ValidationError("run manifest requires exactly 27 scored samples")
    sample_ids = [record.sample_id for record in records]
    if len(set(sample_ids)) != len(sample_ids):
        raise ValidationError("sample IDs must be globally unique")
    anchor_sample_ids = {
        sample_id
        for anchor in anchors
        for sample_id in (
            anchor.left_sample_id,
            anchor.right_sample_id,
            anchor.intact_sample_id,
            anchor.degraded_sample_id,
        )
    }
    overlap = sorted(set(sample_ids) & anchor_sample_ids)
    if overlap:
        raise ValidationError(f"scored and anchor sample IDs must be disjoint: {overlap}")
    triplets: dict[tuple[str, int], list[GateSampleRecord]] = {}
    triplet_ids: dict[tuple[str, int], str] = {}
    for record in records:
        key = (record.brief_id, record.run_index)
        triplets.setdefault(key, []).append(record)
        prior = triplet_ids.setdefault(key, record.triplet_id)
        if prior != record.triplet_id:
            raise ValidationError(f"sample records disagree on triplet ID for {key}")
    briefs = sorted({record.brief_id for record in records})
    if len(briefs) != 3:
        raise ValidationError("run manifest requires exactly three primary briefs")
    if set(triplets) != {(brief, run) for brief in briefs for run in (1, 2, 3)}:
        raise ValidationError("each brief must contain exactly runs 1, 2, and 3")
    seen_triplets: set[str] = set()
    triplet_rows: list[dict[str, Any]] = []
    condition_order = {condition: index for index, condition in enumerate(_CONDITIONS)}
    for key in sorted(triplets):
        rows = triplets[key]
        if len(rows) != 3 or {row.condition for row in rows} != set(_CONDITIONS):
            raise ValidationError(f"triplet {key} must contain one sample for each condition")
        triplet_id = triplet_ids[key]
        if triplet_id in seen_triplets:
            raise ValidationError("triplet IDs must be globally unique")
        seen_triplets.add(triplet_id)
        triplet_rows.append(
            {
                "triplet_id": triplet_id,
                "brief_id": key[0],
                "run_index": key[1],
                "samples": [
                    _sample_manifest(row)
                    for row in sorted(rows, key=lambda item: condition_order[item.condition])
                ],
            }
        )
    anchor_rows = [
        {
            "anchor_id": item.anchor_id,
            "dimensions": list(item.dimensions),
            "left_sample_id": item.left_sample_id,
            "right_sample_id": item.right_sample_id,
            "intact_sample_id": item.intact_sample_id,
            "degraded_sample_id": item.degraded_sample_id,
            "response_mode": item.response_mode,
        }
        for item in anchors
    ]
    return {
        "run_manifest_version": version,
        "protocol_hash": protocol,
        "run_mode": mode,
        "unblinding_confidential": True,
        "anchor_manifest_hash": anchor_hash,
        "anchor_tasks": anchor_rows,
        "triplets": triplet_rows,
    }


def _manifest_parts(
    source: Mapping[str, Any] | Iterable[GateSampleRecord | Mapping[str, Any]],
    anchor_tasks: Iterable[AnchorTaskRecord | Mapping[str, Any]] | None,
) -> tuple[list[dict[str, Any]], tuple[AnchorTaskRecord, ...]]:
    if isinstance(source, Mapping):
        raw_triplets = source.get("triplets")
        raw_anchors = source.get("anchor_tasks") if anchor_tasks is None else anchor_tasks
        if not isinstance(raw_triplets, Sequence) or isinstance(raw_triplets, (str, bytes)):
            raise ValidationError("manifest triplets must be a sequence")
        if raw_anchors is None or not isinstance(raw_anchors, Sequence):
            raise ValidationError("manifest anchor_tasks must be supplied")
        rows: list[dict[str, Any]] = []
        for triplet in raw_triplets:
            item = _mapping(triplet, "manifest triplet")
            triplet_id = _nonempty(item.get("triplet_id"), "triplet_id")
            brief_id = _nonempty(item.get("brief_id"), "brief_id")
            samples = item.get("samples")
            if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)):
                raise ValidationError("manifest triplet samples must be a sequence")
            for sample in samples:
                row = _mapping(sample, "manifest sample")
                sample_id = _nonempty(row.get("sample_id"), "sample_id")
                rows.append(
                    {
                        "sample_id": sample_id,
                        "triplet_id": triplet_id,
                        "brief_id": brief_id,
                    }
                )
        return rows, _validate_anchors(raw_anchors)
    if anchor_tasks is None:
        raise ValidationError("anchor_tasks are required for sample-record projection")
    records = tuple(_coerce_sample(value) for value in source)
    return [
        {
            "sample_id": item.sample_id,
            "triplet_id": item.triplet_id,
            "brief_id": item.brief_id,
        }
        for item in records
    ], _validate_anchors(anchor_tasks)


def _assignment_value(value: Any, sample_id: str) -> tuple[str, str]:
    if isinstance(value, str):
        raise ValidationError(f"opaque assignment for {sample_id} needs label and content_token")
    raw = _mapping(value, f"opaque assignment for {sample_id}")
    allowed = {"sample_label", "opaque_label", "label", "content_token"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValidationError(f"opaque assignment has unsupported fields: {unknown}")
    label = raw.get("sample_label", raw.get("opaque_label", raw.get("label")))
    content = raw.get("content_token")
    return _nonempty(label, f"opaque label for {sample_id}"), _nonempty(
        content, f"opaque content_token for {sample_id}"
    )


def _reject_admin_substrings(value: str, admin_ids: Iterable[str], label: str) -> None:
    lowered = value.casefold()
    for admin_id in admin_ids:
        candidate = str(admin_id).strip()
        if candidate and candidate.casefold() in lowered:
            raise ValidationError(f"{label} may not expose an admin identifier")


def build_rater_projection(
    manifest_or_samples: Mapping[str, Any] | Iterable[GateSampleRecord | Mapping[str, Any]],
    opaque_labels: Mapping[str, Any],
    *,
    anchor_tasks: Iterable[AnchorTaskRecord | Mapping[str, Any]] | None = None,
    opaque_task_ids: Mapping[str, str] | None = None,
    opaque_triplet_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Create a blinded projection using only pre-frozen opaque assignments.

    No condition, run index, brief ID, anchor role, or unblinding map is
    emitted.  ``opaque_labels`` must cover every primary and anchor sample
    exactly, using ``{"label": ..., "content_token": ...}`` values.
    """

    primary_rows, anchors = _manifest_parts(manifest_or_samples, anchor_tasks)
    if not isinstance(opaque_labels, Mapping):
        raise ValidationError("opaque_labels must be a mapping")
    primary_ids = {str(row["sample_id"]) for row in primary_rows}
    source_triplet_ids = {str(row["triplet_id"]) for row in primary_rows}
    source_brief_ids = {str(row["brief_id"]) for row in primary_rows}
    anchor_ids = {
        item_id
        for item in anchors
        for item_id in (
            item.left_sample_id,
            item.right_sample_id,
            item.intact_sample_id,
            item.degraded_sample_id,
        )
    }
    expected_ids = primary_ids | anchor_ids
    admin_ids = (
        primary_ids
        | anchor_ids
        | source_triplet_ids
        | source_brief_ids
        | {item.anchor_id for item in anchors}
    )
    if set(str(key) for key in opaque_labels) != expected_ids:
        missing = sorted(expected_ids - {str(key) for key in opaque_labels})
        extra = sorted({str(key) for key in opaque_labels} - expected_ids)
        raise ValidationError(f"opaque label coverage mismatch: missing={missing}, extra={extra}")
    assignments: dict[str, tuple[str, str]] = {}
    for sample_id in sorted(expected_ids):
        raw_value = opaque_labels[sample_id]
        assignments[sample_id] = _assignment_value(raw_value, sample_id)
    labels = [value[0] for value in assignments.values()]
    if len(set(labels)) != len(labels):
        raise ValidationError("opaque sample labels must be unique")
    content_tokens = [value[1].casefold() for value in assignments.values()]
    if len(set(content_tokens)) != len(content_tokens):
        raise ValidationError("opaque content tokens must be unique")
    reserved_tokens = (*_CONDITIONS, "intact", "degraded", "left", "right", "forced_choice")
    for sample_id, (label, content_token) in assignments.items():
        source_sample_id = sample_id.casefold()
        if label.casefold() == source_sample_id or content_token.casefold() == source_sample_id:
            raise ValidationError("opaque assignments may not expose source sample IDs")
        lowered = f"{label} {content_token}".casefold()
        if any(token in lowered for token in reserved_tokens):
            raise ValidationError("opaque assignments may not expose condition or anchor roles")
        _reject_admin_substrings(label, admin_ids, "opaque labels")
        _reject_admin_substrings(content_token, admin_ids, "opaque content tokens")
    if opaque_task_ids is None or set(opaque_task_ids) != {item.anchor_id for item in anchors}:
        raise ValidationError("opaque task IDs must exactly cover the anchor tasks")
    assert opaque_task_ids is not None
    task_id_source = opaque_task_ids
    task_ids = {
        item.anchor_id: _nonempty(task_id_source[item.anchor_id], "opaque task ID")
        for item in anchors
    }
    if len(set(task_ids.values())) != len(task_ids):
        raise ValidationError("opaque task IDs must be unique")
    if any(task_ids[item.anchor_id] == item.anchor_id for item in anchors):
        raise ValidationError("opaque task IDs may not expose anchor IDs")
    if any(
        any(token in task_id.lower() for token in ("intact", "degraded", *_CONDITIONS))
        for task_id in task_ids.values()
    ):
        raise ValidationError("opaque task IDs may not expose anchor roles or conditions")
    for task_id in task_ids.values():
        _reject_admin_substrings(task_id, admin_ids, "opaque task IDs")
    if opaque_triplet_ids is None:
        raise ValidationError("opaque_triplet_ids are required")
    expected_triplets = source_triplet_ids
    if set(str(key) for key in opaque_triplet_ids) != expected_triplets:
        missing = sorted(expected_triplets - {str(key) for key in opaque_triplet_ids})
        extra = sorted({str(key) for key in opaque_triplet_ids} - expected_triplets)
        raise ValidationError(
            f"opaque triplet ID coverage mismatch: missing={missing}, extra={extra}"
        )
    triplet_ids = {
        triplet_id: _nonempty(opaque_triplet_ids[triplet_id], "opaque triplet ID")
        for triplet_id in sorted(expected_triplets)
    }
    if len(set(triplet_ids.values())) != len(triplet_ids):
        raise ValidationError("opaque triplet IDs must be unique")
    for triplet_id in triplet_ids.values():
        if any(token in triplet_id.casefold() for token in ("intact", "degraded", *_CONDITIONS)):
            raise ValidationError("opaque triplet IDs may not expose conditions or anchor roles")
        _reject_admin_substrings(triplet_id, admin_ids, "opaque triplet IDs")
    triplets: dict[str, list[dict[str, str]]] = {}
    for row in primary_rows:
        triplet_id = str(row["triplet_id"])
        sample_id = str(row["sample_id"])
        label, content_token = assignments[sample_id]
        triplets.setdefault(triplet_id, []).append(
            {"sample_label": label, "content_token": content_token}
        )
    triplet_rows: list[dict[str, Any]] = []
    for source_triplet_id, rows in sorted(triplets.items()):
        triplet_rows.append(
            {
                "triplet_id": triplet_ids[source_triplet_id],
                "samples": sorted(rows, key=lambda row: row["sample_label"]),
            }
        )
    task_rows: list[dict[str, Any]] = []
    for anchor in anchors:
        left_label, left_token = assignments[anchor.left_sample_id]
        right_label, right_token = assignments[anchor.right_sample_id]
        task_rows.append(
            {
                "task_id": task_ids[anchor.anchor_id],
                "dimensions": list(anchor.dimensions),
                "left": {"sample_label": left_label, "content_token": left_token},
                "right": {"sample_label": right_label, "content_token": right_token},
                "response_mode": anchor.response_mode,
            }
        )
    return {"triplets": triplet_rows, "anchor_tasks": task_rows}


__all__ = ["AnchorTaskRecord", "GateSampleRecord", "build_rater_projection", "build_run_manifest"]
