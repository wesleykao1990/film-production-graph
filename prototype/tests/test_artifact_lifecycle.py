from __future__ import annotations


def _node_by_type(client, artifact_type: str):
    lineage = client.get("/api/projects/project_blue_pen/lineage").json()
    return next(node for node in lineage["nodes"] if node["artifact_type"] == artifact_type)


def test_new_version_preserves_locked_payload_and_marks_descendants(client):
    scene = _node_by_type(client, "scene_contract")
    original = scene["current_version"]
    assert original["status"] == "locked"

    new_payload = dict(original["payload"])
    new_payload["revision_note"] = "Test revision"
    response = client.post(
        f"/api/artifacts/{scene['id']}/versions",
        json={"payload": new_payload, "status": "draft", "created_by": "test-human"},
    )
    assert response.status_code == 200
    revised = response.json()
    assert revised["version_number"] == 2
    assert revised["status"] == "draft"
    assert revised["content_hash"] != original["content_hash"]

    artifact = client.get(f"/api/artifacts/{scene['id']}").json()
    versions = artifact["versions"]
    assert versions[1]["id"] == original["id"]
    assert versions[1]["status"] == "locked"
    assert versions[1]["payload"] == original["payload"]

    lineage = client.get("/api/projects/project_blue_pen/lineage").json()
    impacted_types = {item["affected_type"] for item in lineage["impacts"]}
    assert "screenplay_scene" in impacted_types
    assert "shot_contract" in impacted_types


def test_approval_and_lock_are_separate_human_actions(client):
    shot = _node_by_type(client, "shot_contract")
    version_id = shot["current_version"]["id"]

    premature_lock = client.post(
        f"/api/versions/{version_id}/lock",
        json={"rationale": "Should fail"},
    )
    assert premature_lock.status_code == 409

    approved = client.post(
        f"/api/versions/{version_id}/approve",
        json={"rationale": "Shot contract is ready for canonical review."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    locked = client.post(
        f"/api/versions/{version_id}/lock",
        json={"rationale": "Lock the approved shot contract."},
    )
    assert locked.status_code == 200
    assert locked.json()["status"] == "locked"
