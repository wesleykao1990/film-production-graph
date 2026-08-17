"""Narrow provider-neutral ports.

The ports are intentionally synchronous for M00.  A later runtime can adapt
them to async jobs without changing request/response contracts.
"""

from __future__ import annotations

from typing import Protocol

from film_graph.contracts.provider import (
    MediaRequest,
    MediaResponse,
    ModelRequest,
    ModelResponse,
)


class TextModelPort(Protocol):
    """Generate text from a structured request."""

    def complete(self, request: ModelRequest) -> ModelResponse: ...


class MediaProviderPort(Protocol):
    """Generate deterministic or provider-backed media bytes."""

    def generate(self, request: MediaRequest) -> MediaResponse: ...
