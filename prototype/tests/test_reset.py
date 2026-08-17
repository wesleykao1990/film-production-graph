from __future__ import annotations


def test_reset_restores_deterministic_fixture(client):
    client.post("/api/demo/revise-scene-contract")
    before = client.get("/api/projects/project_blue_pen/lineage").json()
    assert before["impacts"]

    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200

    after = client.get("/api/projects/project_blue_pen/lineage").json()
    assert len(after["nodes"]) == 10
    assert after["impacts"] == []
    scene = next(node for node in after["nodes"] if node["artifact_type"] == "scene_contract")
    assert scene["current_version"]["version_number"] == 1
    assert scene["current_version"]["status"] == "locked"
