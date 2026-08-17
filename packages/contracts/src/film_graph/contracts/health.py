"""Wire-level health response contract."""

from __future__ import annotations

from typing import Literal, TypedDict


class HealthResponse(TypedDict):
    status: Literal["ok"]
    service: str
    version: str
