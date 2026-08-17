from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from film_graph.domain import FoundationBoundary


def test_foundation_boundary_records_m00_authority_invariants() -> None:
    boundary = FoundationBoundary()
    assert boundary.milestone == "M00"
    assert boundary.canonical_store == "postgres"
    assert boundary.agents_may_approve is False
    with pytest.raises(FrozenInstanceError):
        boundary.agents_may_approve = True  # type: ignore[assignment,misc]


def test_domain_source_has_no_framework_or_future_domain_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages/domain/src"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    lowered = source.lower()
    for forbidden in (
        "fastapi",
        "pydantic_ai",
        "supabase",
        "prototype",
        "provider sdk",
        "artifactversion",
        "lifecyclestatus",
    ):
        assert forbidden not in lowered
