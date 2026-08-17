"""Provider-neutral request/response contracts.

No provider client or network transport is represented here.  Implementations
can be deterministic fakes in M00 and real adapters in later milestones.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelRequest:
    prompt: str
    model: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    model: str
    provider: str
    request_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MediaRequest:
    kind: str
    prompt: str
    model: str
    settings: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MediaResponse:
    data: bytes
    media_type: str
    provider: str
    model: str
    request_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
