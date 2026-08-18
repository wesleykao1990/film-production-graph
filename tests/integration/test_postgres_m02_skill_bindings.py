from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytest.importorskip("psycopg")

from film_graph.application import (  # noqa: E402
    BindProjectSkillCommand,
    CreateProjectCommand,
    FilmGraphApplicationService,
)
from film_graph.domain import ActorRef, ActorType  # noqa: E402
from film_graph.persistence import PostgresGraphRepository  # noqa: E402

COMMIT = "e64ef1e5b33c14dc23cc85e9d6f1b466a99634aa"
CONTENT_HASH = "sha256:" + ("a" * 64)
SNAPSHOT_HASH = "sha256:" + ("b" * 64)


@pytest.fixture
def service() -> FilmGraphApplicationService:
    dsn = os.getenv("FPG_DATABASE_URL")
    if not dsn:
        pytest.skip("FPG_DATABASE_URL is not configured; Postgres integration is opt-in")
    repository = PostgresGraphRepository(dsn)
    repository.ping()
    return FilmGraphApplicationService(repository)


def test_binding_survives_repository_restart_and_is_append_only(
    service: FilmGraphApplicationService,
) -> None:
    import psycopg

    actor = ActorRef(ActorType.USER, f"integration-{uuid4()}")
    project = service.create_project(CreateProjectCommand(f"M02 binding {uuid4()}"))
    binding = service.bind_project_skill(
        BindProjectSkillCommand(
            project_id=project.id,
            agent_ref="screenplay-agent",
            skill_name="subtext-pass",
            source_path="skills/subtext-pass",
            source_commit=COMMIT,
            content_hash=CONTENT_HASH,
            metadata_version="1.0.0",
            snapshot_hash=SNAPSHOT_HASH,
            actor=actor,
        )
    )

    restarted = FilmGraphApplicationService(PostgresGraphRepository(os.environ["FPG_DATABASE_URL"]))
    assert restarted.get_project_skill_binding(
        project.id, "screenplay-agent", "subtext-pass"
    ) == binding
    assert restarted.list_project_skill_bindings(project.id) == [binding]

    replacement = restarted.bind_project_skill(
        BindProjectSkillCommand(
            project_id=project.id,
            agent_ref="screenplay-agent",
            skill_name="subtext-pass",
            source_path="skills/subtext-pass",
            source_commit="0123456789abcdef0123456789abcdef01234567",
            content_hash="sha256:" + ("c" * 64),
            metadata_version="1.0.1",
            snapshot_hash="sha256:" + ("d" * 64),
            actor=actor,
        )
    )
    assert restarted.get_project_skill_binding(
        project.id, "screenplay-agent", "subtext-pass"
    ) == replacement
    assert restarted.list_project_skill_bindings(project.id) == [binding, replacement]

    with psycopg.connect(os.environ["FPG_DATABASE_URL"], autocommit=True) as connection:
        with pytest.raises(psycopg.Error):
            connection.execute(
                "update public.project_skill_locks set source_commit = %s where id = %s",
                ("0123456789abcdef0123456789abcdef01234567", binding.id),
            )
        with pytest.raises(psycopg.Error):
            connection.execute(
                "delete from public.project_skill_locks where id = %s", (binding.id,)
            )

        connection.execute("delete from public.projects where id = %s", (project.id,))
        assert connection.execute(
            "select 1 from public.project_skill_locks where id = %s", (binding.id,)
        ).fetchone() is None
