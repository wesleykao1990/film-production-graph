from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from film_graph.application import (
    BindProjectSkillCommand,
    ConflictError,
    CreateProjectCommand,
    FilmGraphApplicationService,
    InMemoryGraphRepository,
    NotFoundError,
    ValidationError,
)
from film_graph.domain import ActorRef, ActorType
from film_graph.domain.errors import AuthorityError

COMMIT = "e64ef1e5b33c14dc23cc85e9d6f1b466a99634aa"
CONTENT_HASH = "sha256:" + ("a" * 64)
SNAPSHOT_HASH = "sha256:" + ("b" * 64)
CREATED_AT = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
Graph = tuple[FilmGraphApplicationService, InMemoryGraphRepository]


def _command(
    project_id: UUID, *, actor: ActorRef | None = None, **overrides: Any
) -> BindProjectSkillCommand:
    values: dict[str, object] = {
        "project_id": project_id,
        "agent_ref": "screenplay-agent",
        "skill_name": "subtext-pass",
        "source_path": "skills/subtext-pass",
        "source_commit": COMMIT,
        "content_hash": CONTENT_HASH,
        "metadata_version": "1.0.0",
        "snapshot_hash": SNAPSHOT_HASH,
        "actor": actor or ActorRef(ActorType.USER, "producer-1"),
        "created_at": CREATED_AT,
    }
    values.update(overrides)
    return BindProjectSkillCommand(**cast(Any, values))


@pytest.fixture
def graph() -> Graph:
    repository = InMemoryGraphRepository()
    return FilmGraphApplicationService(repository), repository


def test_binding_stores_and_queries_the_full_exact_reference(graph: Graph) -> None:
    service, repository = graph
    project = service.create_project(CreateProjectCommand("M02 binding test"))

    binding = service.bind_project_skill(_command(project.id))

    assert binding.project_id == project.id
    assert binding.source_path == "skills/subtext-pass"
    assert binding.source_commit == COMMIT
    assert binding.content_hash == CONTENT_HASH
    assert binding.snapshot_hash == SNAPSHOT_HASH
    assert service.get_project_skill_binding(
        project.id, "screenplay-agent", "subtext-pass"
    ) == binding
    assert service.list_project_skill_bindings(project.id) == [binding]
    assert repository.project_skill_bindings[binding.id] == binding


def test_binding_requires_existing_project_and_human_actor(graph: Graph) -> None:
    service, _ = graph
    missing = uuid4()
    with pytest.raises(NotFoundError, match="project not found"):
        service.bind_project_skill(_command(missing))

    project = service.create_project(CreateProjectCommand("authority"))
    with pytest.raises(AuthorityError):
        service.bind_project_skill(
            _command(project.id, actor=ActorRef(ActorType.AGENT, "agent-1"))
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("agent_ref", ""),
        ("skill_name", "Subtext Pass"),
        ("source_path", "../outside"),
        ("source_commit", "E64EF1E5B33C14D"),
        ("source_commit", "not-a-commit"),
        ("content_hash", "a" * 64),
        ("content_hash", "sha256:" + ("g" * 64)),
        ("snapshot_hash", "sha256:" + ("c" * 63)),
    ],
)
def test_binding_validates_exact_reference_fields(
    graph: Graph, field: str, value: str
) -> None:
    service, _ = graph
    project = service.create_project(CreateProjectCommand("validation"))
    with pytest.raises(ValidationError):
        service.bind_project_skill(_command(project.id, **cast(Any, {field: value})))


def test_binding_rollover_is_additive_and_same_snapshot_is_unique(graph: Graph) -> None:
    service, _ = graph
    project = service.create_project(CreateProjectCommand("duplicate"))
    first = service.bind_project_skill(_command(project.id))

    with pytest.raises(ConflictError):
        service.bind_project_skill(_command(project.id))

    second = service.bind_project_skill(
        _command(
            project.id,
            source_commit="0123456789abcdef0123456789abcdef01234567",
            content_hash="sha256:" + ("c" * 64),
            snapshot_hash="sha256:" + ("d" * 64),
            created_at=CREATED_AT.replace(microsecond=1),
        )
    )
    assert service.get_project_skill_binding(
        project.id, "screenplay-agent", "subtext-pass"
    ) == second
    assert service.list_project_skill_bindings(project.id) == [first, second]

    with pytest.raises(ConflictError):
        service.bind_project_skill(
            _command(
                project.id,
                source_commit="0123456789abcdef0123456789abcdef01234567",
                content_hash="sha256:" + ("c" * 64),
                snapshot_hash="sha256:" + ("d" * 64),
                created_at=CREATED_AT.replace(microsecond=2),
            )
        )


def test_bindings_are_independent_per_agent_and_skill(graph: Graph) -> None:
    service, _ = graph
    project = service.create_project(CreateProjectCommand("scoping"))
    first = service.bind_project_skill(_command(project.id, agent_ref="agent-a"))
    second = service.bind_project_skill(
        _command(project.id, agent_ref="agent-b", skill_name="other-skill")
    )

    assert service.list_project_skill_bindings(project.id, agent_ref="agent-a") == [first]
    assert service.list_project_skill_bindings(project.id, agent_ref="agent-b") == [second]
