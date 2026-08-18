from fastapi.testclient import TestClient
from film_graph.api.main import create_app
from film_graph.application import FilmGraphApplicationService, InMemoryGraphRepository


def test_m01_api_project_artifact_and_health_smoke() -> None:
    service = FilmGraphApplicationService(InMemoryGraphRepository())
    client = TestClient(create_app(service))
    assert client.get("/health").json()["status"] == "ok"
    project = client.post("/api/projects", json={"name": "API Project"})
    assert project.status_code == 201
    project_id = project.json()["project_id"]
    artifact = client.post(
        f"/api/projects/{project_id}/artifacts",
        json={
            "artifact_type": "creative_constitution",
            "logical_key": "constitution",
            "payload": {"title": "Still Water"},
            "actor": {"actor_type": "user", "actor_id": "human"},
        },
    )
    assert artifact.status_code == 201, artifact.text
    assert artifact.json()["lifecycle_status"] == "draft"
    listed = client.get(f"/api/projects/{project_id}/artifacts")
    assert listed.status_code == 200
    assert listed.json()[0]["logical_key"] == "constitution"


def test_m01_api_without_database_returns_explicit_service_failure() -> None:
    client = TestClient(create_app(None))
    assert client.get("/health").status_code == 200
    assert client.post("/api/projects", json={"name": "unconfigured"}).status_code == 503


def test_m01_api_rejects_agent_approval_and_invalid_edge() -> None:
    service = FilmGraphApplicationService(InMemoryGraphRepository())
    client = TestClient(create_app(service))
    project = client.post("/api/projects", json={"name": "API Validation"}).json()
    project_id = project["project_id"]
    first = client.post(
        f"/api/projects/{project_id}/artifacts",
        json={
            "artifact_type": "sequence",
            "logical_key": "first",
            "payload": {"title": "First"},
            "actor": {"actor_type": "user", "actor_id": "human"},
        },
    ).json()
    second = client.post(
        f"/api/projects/{project_id}/artifacts",
        json={
            "artifact_type": "sequence",
            "logical_key": "second",
            "payload": {"title": "Second"},
            "actor": {"actor_type": "user", "actor_id": "human"},
        },
    ).json()
    approval = client.post(
        f"/api/versions/{first['version_id']}/approve",
        json={
            "expected_current_revision": 1,
            "actor": {"actor_type": "agent", "actor_id": "agent-1"},
        },
    )
    assert approval.status_code in {409, 422}
    edge = client.post(
        "/api/edges",
        json={
            "project_id": project_id,
            "from_version_id": first["version_id"],
            "to_version_id": second["version_id"],
            "edge_type": "NOT_AN_M01_EDGE",
        },
    )
    assert edge.status_code in {409, 422}
    assert first["artifact_type"] == "sequence"
