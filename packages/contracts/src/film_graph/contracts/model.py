"""Provider-neutral model routing contracts.

These structures are intentionally plain Python values.  FastAPI/Pydantic
serialization belongs at the API boundary and provider SDK types stay out of
the core contract package.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelAliasContract:
    alias: str
    provider: str
    model: str
    settings: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "provider": self.provider,
            "model": self.model,
            "settings": dict(self.settings),
        }


@dataclass(frozen=True, slots=True)
class ResolvedModelContract:
    alias: str
    provider: str
    model: str

    @property
    def resolved_model_id(self) -> str:
        return f"{self.provider}/{self.model}"

    def as_dict(self) -> dict[str, str]:
        return {
            "alias": self.alias,
            "provider": self.provider,
            "model": self.model,
            "resolved_model_id": self.resolved_model_id,
        }
