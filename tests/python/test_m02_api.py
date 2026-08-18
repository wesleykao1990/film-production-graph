import shutil
from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from film_graph.api.main import create_app
from film_graph.application import FilmGraphApplicationService, InMemoryGraphRepository
from film_graph.skills import SkillRegistry

ROOT = Path(__file__).resolve().parents[2]
USER = {"actor_type": "user", "actor_id": "reviewer-1"}
AGENT = {"actor_type": "agent", "actor_id": "screenwriter-1"}


def loaded_registry() -> SkillRegistry:
    registry = SkillRegistry(
        repository_root=ROOT,
        skill_roots=[Path("skills")],
        lock_path=Path("skills.lock"),
    )
    registry.reload()
    return registry


def test_bind_and_fake_run_record_exact_skill_provenance() -> None:
    repository = InMemoryGraphRepository()
    client = TestClient(
        create_app(FilmGraphApplicationService(repository), loaded_registry())
    )
    project_id = client.post("/api/projects", json={"name": "Skill Film"}).json()[
        "project_id"
    ]
    catalog = client.get("/api/skills")
    assert catalog.status_code == 200
    exact_ref = catalog.json()["skills"][0]["locked_ref"]

    bound = client.post(
        f"/api/projects/{project_id}/skill-bindings",
        json={"agent_ref": "screenwriter", "skill_name": "subtext-pass", "actor": USER},
    )
    assert bound.status_code == 201, bound.text
    assert bound.json()["content_hash"] == exact_ref["content_hash"]
    assert bound.json()["source_commit"] == exact_ref["source_commit"]

    response = client.post(
        f"/api/projects/{project_id}/skills/subtext-pass/fake-run",
        json={"agent_ref": "screenwriter", "actor": AGENT},
    )
    assert response.status_code == 201, response.text
    assert response.json()["provenance"]["mode"] == "fake_no_provider"
    assert response.json()["provenance"]["skills"] == [exact_ref]
    stored = next(iter(repository.runs.values()))
    assert stored.resolved_provider is None
    assert stored.provenance["skills"][0]["content_hash"] == exact_ref["content_hash"]


def test_bind_requires_human_and_fake_run_requires_exact_binding() -> None:
    client = TestClient(
        create_app(
            FilmGraphApplicationService(InMemoryGraphRepository()), loaded_registry()
        )
    )
    project_id = client.post("/api/projects", json={"name": "Authority Film"}).json()[
        "project_id"
    ]
    rejected = client.post(
        f"/api/projects/{project_id}/skill-bindings",
        json={"agent_ref": "screenwriter", "skill_name": "subtext-pass", "actor": AGENT},
    )
    assert rejected.status_code == 422
    unbound = client.post(
        f"/api/projects/{project_id}/skills/subtext-pass/fake-run",
        json={"agent_ref": "screenwriter", "actor": AGENT},
    )
    assert unbound.status_code == 404


def test_reload_requires_human_and_unconfigured_registry_is_explicit() -> None:
    service = FilmGraphApplicationService(InMemoryGraphRepository())
    client = TestClient(create_app(service, loaded_registry()))
    assert client.post("/api/skills/reload", json={"actor": AGENT}).status_code == 422
    assert client.post("/api/skills/reload", json={"actor": USER}).status_code == 200
    assert TestClient(create_app(service)).get("/api/skills").status_code == 503


def test_human_can_append_new_exact_binding_after_reviewed_reload(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    shutil.copytree(ROOT / "skills", repository_root / "skills")
    shutil.copytree(ROOT / "schemas", repository_root / "schemas")
    shutil.copy2(ROOT / "skills.lock", repository_root / "skills.lock")
    registry = SkillRegistry(
        repository_root=repository_root,
        skill_roots=[Path("skills")],
        lock_path=Path("skills.lock"),
    )
    registry.reload()
    repository = InMemoryGraphRepository()
    client = TestClient(create_app(FilmGraphApplicationService(repository), registry))
    project_id = client.post("/api/projects", json={"name": "Rollover Film"}).json()[
        "project_id"
    ]
    binding_request = {
        "agent_ref": "screenwriter",
        "skill_name": "subtext-pass",
        "actor": USER,
    }
    binding_url = f"/api/projects/{project_id}/skill-bindings"
    assert client.post(binding_url, json=binding_request).status_code == 201

    method = repository_root / "skills/subtext-pass/references/method.md"
    method.write_text(method.read_text(encoding="utf-8") + "\nReviewed revision.\n")
    new_lock = registry.generate_lock("0123456789abcdef0123456789abcdef01234567")
    (repository_root / "skills.lock").write_text(
        yaml.safe_dump(new_lock, sort_keys=False), encoding="utf-8"
    )
    assert client.post("/api/skills/reload", json={"actor": USER}).status_code == 200
    run_url = f"/api/projects/{project_id}/skills/subtext-pass/fake-run"
    run_request = {"agent_ref": "screenwriter", "actor": AGENT}
    assert client.post(run_url, json=run_request).status_code == 409

    rebound = client.post(binding_url, json=binding_request)
    assert rebound.status_code == 201, rebound.text
    assert client.post(run_url, json=run_request).status_code == 201
    assert len(client.get(binding_url).json()) == 2
