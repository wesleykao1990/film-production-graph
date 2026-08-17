from pathlib import Path

import pytest
from film_graph.application import ApplicationModelResolver
from film_graph.model_routing import (
    InvalidModelAlias,
    ModelAliasRegistry,
    UnknownModelAlias,
)


def test_application_owned_alias_resolves_and_records_concrete_target() -> None:
    resolver = ApplicationModelResolver(
        {
            "aliases": {
                "premise_writer": {
                    "provider": "fake",
                    "model": "fake-text-v1",
                    "settings": {"temperature": 0},
                }
            }
        }
    )
    assert resolver.resolve_for_run("premise_writer") == {
        "alias": "premise_writer",
        "provider": "fake",
        "model": "fake-text-v1",
        "resolved_model_id": "fake/fake-text-v1",
        "settings": {"temperature": 0},
    }


def test_unknown_alias_fails_closed_without_provider_fallback() -> None:
    resolver = ApplicationModelResolver({"aliases": {}})
    with pytest.raises(UnknownModelAlias):
        resolver.resolve("not_configured")


def test_malformed_alias_is_rejected() -> None:
    with pytest.raises(InvalidModelAlias):
        ModelAliasRegistry.from_mapping({"aliases": {"writer": {"provider": "fake"}}})


def test_registry_is_read_only_at_the_lookup_boundary() -> None:
    registry = ModelAliasRegistry({"writer": {"provider": "fake", "model": "text"}})
    assert len(registry) == 1
    with pytest.raises(TypeError):
        registry.aliases["other"] = registry.aliases["writer"]  # type: ignore[index]


def test_checked_in_alias_config_resolves_to_fake_models() -> None:
    config = (
        Path(__file__).resolve().parents[2]
        / "machine-readable"
        / "model-aliases.example.json"
    )
    resolved = ModelAliasRegistry.from_json_file(config).resolve("story_test")
    assert resolved.resolved_model_id == "fake/deterministic-story-test-v1"
