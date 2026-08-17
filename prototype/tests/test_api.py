from __future__ import annotations


def test_health_seed_and_lineage(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["projects"] == 1
    assert body["mode"] == "deterministic-reference-prototype"

    lineage = client.get("/api/projects/project_blue_pen/lineage")
    assert lineage.status_code == 200
    payload = lineage.json()
    assert len(payload["nodes"]) == 10
    assert len(payload["edges"]) == 9
    assert payload["impacts"] == []

    skills = client.get("/api/skills").json()
    assert any(skill["name"] == "subtext-pass" for skill in skills)

    workflows = client.get("/api/workflows").json()
    assert any(workflow["name"] == "prototype-subtext-review" for workflow in workflows)


def test_static_interface_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Film Production Graph" in response.text
    assert "Run subtext workflow" in response.text
