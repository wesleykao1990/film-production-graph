"""Deterministic, offline model/provider implementations for M00 tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from film_graph.contracts.provider import (
    MediaRequest,
    MediaResponse,
    ModelRequest,
    ModelResponse,
)


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _request_data(request: ModelRequest | MediaRequest) -> dict[str, Any]:
    if isinstance(request, ModelRequest):
        return {
            "kind": "model",
            "prompt": request.prompt,
            "model": request.model,
            "metadata": dict(request.metadata),
        }
    return {
        "kind": "media",
        "kind_name": request.kind,
        "prompt": request.prompt,
        "model": request.model,
        "settings": dict(request.settings),
    }


@dataclass(frozen=True, slots=True)
class ProposedOutput:
    """An agent proposal; it deliberately has no approval authority."""

    artifact_type: str
    payload: Mapping[str, Any]
    status: str = "proposed"
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if self.status != "proposed":
            raise ValueError("agent outputs must start in proposed status")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        if not self.fingerprint:
            object.__setattr__(
                self,
                "fingerprint",
                _fingerprint(
                    {
                        "artifact_type": self.artifact_type,
                        "payload": dict(self.payload),
                    }
                ),
            )


@dataclass
class DeterministicFakeModel:
    """A byte-stable text model that never opens a network connection."""

    provider: str = "fake"
    model: str = "fake-text-v1"
    seed: str = "m00"
    _calls: list[ModelRequest] = field(default_factory=list, init=False, repr=False)

    def complete(self, request: ModelRequest | str, *, model: str | None = None) -> ModelResponse:
        if isinstance(request, str):
            request = ModelRequest(prompt=request, model=model or self.model)
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be ModelRequest or str")
        self._calls.append(request)
        data = _request_data(request)
        fingerprint = _fingerprint({"seed": self.seed, **data})
        # Keep output deterministic and useful for snapshots, while avoiding a
        # claim that a fake response is creative truth.
        text = f"[fake:{request.model}:{fingerprint[:16]}] {request.prompt.strip()}"
        return ModelResponse(
            text=text,
            model=request.model,
            provider=self.provider,
            request_fingerprint=fingerprint,
            metadata={"deterministic": True, "network": "disabled", "seed": self.seed},
        )

    def run(self, prompt: str, *, model: str | None = None) -> ModelResponse:
        return self.complete(prompt, model=model)

    @property
    def calls(self) -> tuple[ModelRequest, ...]:
        return tuple(self._calls)


@dataclass
class DeterministicFakeProvider:
    """Provider-port implementation returning stable, local bytes."""

    provider: str = "fake"
    model: str = "fake-media-v1"
    seed: str = "m00"
    _calls: list[MediaRequest] = field(default_factory=list, init=False, repr=False)

    def generate(self, request: MediaRequest | str, *, kind: str = "image") -> MediaResponse:
        if isinstance(request, str):
            request = MediaRequest(kind=kind, prompt=request, model=self.model)
        if not isinstance(request, MediaRequest):
            raise TypeError("request must be MediaRequest or str")
        self._calls.append(request)
        data = _request_data(request)
        fingerprint = _fingerprint({"seed": self.seed, **data})
        # The bytes are a deterministic test artifact, not a claim to be a
        # playable image/video.  Media validation belongs to later milestones.
        payload = f"fake-media:{request.kind}:{fingerprint}\n".encode("ascii")
        return MediaResponse(
            data=payload,
            media_type=f"application/x-fake-{request.kind}",
            provider=self.provider,
            model=request.model,
            request_fingerprint=fingerprint,
            metadata={"deterministic": True, "network": "disabled", "seed": self.seed},
        )

    @property
    def calls(self) -> tuple[MediaRequest, ...]:
        return tuple(self._calls)


class DeterministicFakeAgent:
    """Minimal proposal-only agent facade for authority tests."""

    def __init__(self, model: DeterministicFakeModel | None = None) -> None:
        self.model = model or DeterministicFakeModel()

    def propose(
        self,
        artifact_type: str,
        payload: Mapping[str, Any],
    ) -> ProposedOutput:
        return ProposedOutput(artifact_type=artifact_type, payload=payload)


# Friendly short aliases for test/application code.
FakeModel = DeterministicFakeModel
FakeProvider = DeterministicFakeProvider
FakeAgent = DeterministicFakeAgent
