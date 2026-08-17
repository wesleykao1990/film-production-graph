from __future__ import annotations

import json
from pathlib import Path

from .repository import Repository


def seed_if_empty(repository: Repository, seed_path: Path) -> None:
    if repository.project_count() > 0:
        return
    seed(repository, seed_path)


def seed(repository: Repository, seed_path: Path) -> None:
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    project = data["project"]
    repository.create_project(project["id"], project["name"], project["description"])
    for artifact in data["artifacts"]:
        repository.create_artifact_with_version(
            project_id=project["id"],
            artifact_type=artifact["artifact_type"],
            title=artifact["title"],
            payload=artifact["payload"],
            status=artifact.get("status", "draft"),
            created_by=artifact.get("created_by", "seed"),
            artifact_id=artifact["id"],
            version_id=artifact["version_id"],
        )
    for edge in data["edges"]:
        repository.add_edge(
            project["id"], edge["parent"], edge["child"], edge.get("edge_type", "depends_on")
        )
