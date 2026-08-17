"""Application service for resolving and recording model aliases."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from film_graph.model_routing import ModelAliasRegistry, ResolvedModel


class ApplicationModelResolver:
    """Own alias lookup at the application boundary.

    Callers receive a resolved value containing both the configured alias and
    concrete provider/model.  There is no implicit environment or provider
    lookup, which keeps run provenance deterministic.
    """

    def __init__(self, config: Mapping[str, Any] | ModelAliasRegistry) -> None:
        self._registry = (
            config
            if isinstance(config, ModelAliasRegistry)
            else ModelAliasRegistry.from_mapping(config)
        )

    @property
    def registry(self) -> ModelAliasRegistry:
        return self._registry

    def resolve(self, alias: str) -> ResolvedModel:
        return self._registry.resolve(alias)

    def resolve_for_run(self, alias: str) -> dict[str, Any]:
        """Return the serializable provenance fields a run should persist."""

        resolved = self.resolve(alias)
        return resolved.as_dict()


def resolve_model_alias(
    alias: str,
    config: Mapping[str, Any] | ModelAliasRegistry,
) -> ResolvedModel:
    """Convenience entry point owned by the application package."""

    return ApplicationModelResolver(config).resolve(alias)
