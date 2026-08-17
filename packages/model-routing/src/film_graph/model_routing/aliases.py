"""Application-owned aliases and resolved model recording.

The resolver intentionally has no provider SDK or network fallback.  An alias
must be present in the supplied application configuration; accepting arbitrary
provider/model strings at the call site would make provenance non-reproducible.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from film_graph.contracts.model import ModelAliasContract, ResolvedModelContract

from .errors import InvalidModelAlias, ModelRoutingError, UnknownModelAlias


def _validate_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidModelAlias(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ModelAlias:
    """One configured alias and its provider/model target."""

    name: str
    provider: str
    model: str
    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_text(self.name, "alias name"))
        object.__setattr__(self, "provider", _validate_text(self.provider, "provider"))
        object.__setattr__(self, "model", _validate_text(self.model, "model"))
        object.__setattr__(self, "settings", MappingProxyType(dict(self.settings)))

    @property
    def resolved_model_id(self) -> str:
        return f"{self.provider}/{self.model}"

    def contract(self) -> ModelAliasContract:
        return ModelAliasContract(
            alias=self.name,
            provider=self.provider,
            model=self.model,
            settings=self.settings,
        )


@dataclass(frozen=True, slots=True)
class ResolvedModel:
    """The immutable routing decision recorded on a run."""

    alias: str
    provider: str
    model: str
    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "alias", _validate_text(self.alias, "alias"))
        object.__setattr__(self, "provider", _validate_text(self.provider, "provider"))
        object.__setattr__(self, "model", _validate_text(self.model, "model"))
        object.__setattr__(self, "settings", MappingProxyType(dict(self.settings)))

    @property
    def resolved_model_id(self) -> str:
        return f"{self.provider}/{self.model}"

    def contract(self) -> ResolvedModelContract:
        return ResolvedModelContract(
            alias=self.alias,
            provider=self.provider,
            model=self.model,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "provider": self.provider,
            "model": self.model,
            "resolved_model_id": self.resolved_model_id,
            "settings": dict(self.settings),
        }


class ModelAliasRegistry:
    """Read-only registry owned by the application layer."""

    def __init__(self, aliases: Mapping[str, ModelAlias | Mapping[str, Any]]) -> None:
        normalized: dict[str, ModelAlias] = {}
        for name, entry in aliases.items():
            alias = entry if isinstance(entry, ModelAlias) else self._from_entry(name, entry)
            if alias.name in normalized:
                raise InvalidModelAlias(f"duplicate model alias: {alias.name}")
            normalized[alias.name] = alias
        self._aliases = MappingProxyType(normalized)

    @staticmethod
    def _from_entry(name: str, entry: Mapping[str, Any]) -> ModelAlias:
        if not isinstance(entry, Mapping):
            raise InvalidModelAlias(f"alias {name!r} must be a mapping")
        provider = entry.get("provider")
        model = entry.get("model")
        # Supporting a single resolved_model_id is convenient for checked-in
        # configs while preserving explicit provider/model provenance.
        if (provider is None or model is None) and entry.get("resolved_model_id"):
            resolved = str(entry["resolved_model_id"])
            if "/" not in resolved:
                raise InvalidModelAlias(
                    f"alias {name!r} resolved_model_id must be 'provider/model'"
                )
            provider, model = resolved.split("/", 1)
        return ModelAlias(
            name=name,
            provider=_validate_text(provider, f"alias {name!r} provider"),
            model=_validate_text(model, f"alias {name!r} model"),
            settings=entry.get("settings", {}),
        )

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> ModelAliasRegistry:
        if not isinstance(config, Mapping):
            raise InvalidModelAlias("model routing config must be a mapping")
        aliases = config.get("aliases", config)
        if not isinstance(aliases, Mapping):
            raise InvalidModelAlias("model routing config 'aliases' must be a mapping")
        return cls(aliases)

    @classmethod
    def from_json_file(cls, path: str | Path) -> ModelAliasRegistry:
        config_path = Path(path)
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ModelRoutingError(f"unable to read model routing config: {config_path}") from exc
        except json.JSONDecodeError as exc:
            raise InvalidModelAlias(f"invalid JSON model routing config: {config_path}") from exc
        return cls.from_mapping(config)

    @property
    def aliases(self) -> Mapping[str, ModelAlias]:
        return self._aliases

    def resolve(self, alias: str) -> ResolvedModel:
        try:
            configured = self._aliases[alias]
        except KeyError as exc:
            raise UnknownModelAlias(f"unknown model alias: {alias}") from exc
        return ResolvedModel(
            alias=configured.name,
            provider=configured.provider,
            model=configured.model,
            settings=configured.settings,
        )

    def __contains__(self, alias: object) -> bool:
        return alias in self._aliases

    def __len__(self) -> int:
        return len(self._aliases)


def resolve_model_alias(
    alias: str,
    config: Mapping[str, Any] | ModelAliasRegistry,
) -> ResolvedModel:
    """Resolve ``alias`` using a registry or a plain config mapping."""

    registry = (
        config
        if isinstance(config, ModelAliasRegistry)
        else ModelAliasRegistry.from_mapping(config)
    )
    return registry.resolve(alias)
