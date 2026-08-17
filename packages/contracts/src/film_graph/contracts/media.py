"""Media boundary contracts shared by media and application packages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolAvailability:
    name: str
    executable: str
    available: bool
    version: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "executable": self.executable,
            "available": self.available,
            "version": self.version,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class MediaProbeResult:
    path: str
    streams: tuple[dict[str, Any], ...]
    format: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "streams": [dict(stream) for stream in self.streams],
            "format": dict(self.format),
        }
