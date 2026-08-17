from fastapi.testclient import TestClient
from film_graph.api.main import app


def test_health_is_deterministic_and_has_no_provider_dependency() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "film-production-graph-api",
        "version": "0.1.0",
    }
    assert client.get("/api/health").json() == response.json()


def test_unknown_api_path_is_a_client_failure() -> None:
    assert TestClient(app).get("/not-a-m00-route").status_code == 404
