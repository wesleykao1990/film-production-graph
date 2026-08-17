"""Dependency-free production domain boundary for M00.

Artifact identities, versions, lifecycle rules, lineage, and canonical hashing
are deliberately deferred to M01. Importing this package proves the dependency
boundary without prematurely freezing those public contracts.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class FoundationBoundary:
    milestone: Literal["M00"] = "M00"
    canonical_store: Literal["postgres"] = "postgres"
    agents_may_approve: Literal[False] = False


__all__ = ["FoundationBoundary"]
