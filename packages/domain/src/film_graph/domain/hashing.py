"""Canonical JSON normalization and SHA-256 hashing.

The serializer is deliberately implemented without Pydantic so artifact hashes
remain stable at the domain boundary.  Newline, Unicode, timezone, mapping
order, and common numeric representation differences are normalized before
encoding UTF-8 JSON.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import UUID

_ISO_WITH_ZONE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$"
)


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        normalized_datetime = value if value.tzinfo is None else value.astimezone(UTC)
        return _normalize_text(normalized_datetime.isoformat())
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        normalized_text = _normalize_text(value)
        # Payloads often carry timestamps as strings.  Normalize equivalent
        # offsets while leaving ordinary text untouched.
        if _ISO_WITH_ZONE.match(normalized_text):
            try:
                parsed = datetime.fromisoformat(normalized_text.replace("Z", "+00:00"))
            except ValueError:
                pass
            else:
                normalized_text = parsed.astimezone(UTC).isoformat()
        return normalized_text
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and infinity are not valid canonical JSON values")
        return int(value) if value.is_integer() else value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal is not canonical JSON")
        return int(value) if value == value.to_integral() else float(value)
    if isinstance(value, Mapping):
        normalized_mapping: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = _normalize_text(str(key))
            if normalized_key in normalized_mapping:
                raise ValueError(f"canonical mapping key collision: {normalized_key!r}")
            normalized_mapping[normalized_key] = _normalize(item)
        return normalized_mapping
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized_items = [_normalize(item) for item in value]
        return sorted(
            normalized_items, key=lambda item: json.dumps(item, sort_keys=True, default=str)
        )
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_value(value: Any) -> Any:
    """Return a normalized JSON-compatible value."""

    return _normalize(value)


def to_json_compatible(value: Any) -> Any:
    """Recursively thaw and normalize domain values for JSON/JSONB boundaries.

    Domain payloads are intentionally frozen with ``MappingProxyType`` and
    tuples. Adapters must use this public boundary instead of shallow
    ``dict(...)`` conversion, which leaves nested immutable containers behind.
    """

    return canonical_value(value)


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def content_hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
