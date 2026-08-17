"""Application ports kept independent of web and persistence frameworks."""

from __future__ import annotations

from typing import Protocol

from film_graph.contracts.provider import MediaRequest, MediaResponse, ModelRequest, ModelResponse


class ModelRunner(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...


class MediaRunner(Protocol):
    def generate(self, request: MediaRequest) -> MediaResponse: ...
