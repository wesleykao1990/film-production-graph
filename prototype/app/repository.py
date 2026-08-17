from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .db import Database


ALLOWED_STATUSES = {"draft", "proposed", "approved", "locked", "rejected", "deprecated"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


class RepositoryError(RuntimeError):
    pass


class Repository:
    def __init__(self, database: Database):
        self.database = database

    def project_count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0])

    def create_project(self, project_id: str, name: str, description: str) -> dict[str, Any]:
        created_at = now_iso()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO projects(id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (project_id, name, description, created_at),
            )
        return self.get_project(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM projects ORDER BY created_at").fetchall()
        return [row_to_dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise RepositoryError(f"Unknown project: {project_id}")
        return row_to_dict(row)

    def create_artifact_with_version(
        self,
        *,
        project_id: str,
        artifact_type: str,
        title: str,
        payload: dict[str, Any],
        status: str = "draft",
        created_by: str = "human",
        artifact_id: str | None = None,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        if status not in ALLOWED_STATUSES:
            raise RepositoryError(f"Unsupported status: {status}")
        artifact_id = artifact_id or f"art_{uuid4().hex}"
        version_id = version_id or f"ver_{uuid4().hex}"
        timestamp = now_iso()
        payload_json = canonical_json(payload)
        digest = content_hash(payload)
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO artifacts(id, project_id, artifact_type, title, created_at) VALUES (?, ?, ?, ?, ?)",
                (artifact_id, project_id, artifact_type, title, timestamp),
            )
            connection.execute(
                """
                INSERT INTO artifact_versions(
                    id, artifact_id, version_number, status, payload_json,
                    content_hash, created_by, created_at, approved_at, locked_at
                ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    artifact_id,
                    status,
                    payload_json,
                    digest,
                    created_by,
                    timestamp,
                    timestamp if status in {"approved", "locked"} else None,
                    timestamp if status == "locked" else None,
                ),
            )
        return self.get_artifact(artifact_id)

    def add_edge(
        self,
        project_id: str,
        parent_artifact_id: str,
        child_artifact_id: str,
        edge_type: str,
    ) -> dict[str, Any]:
        if parent_artifact_id == child_artifact_id:
            raise RepositoryError("Self-referential lineage edges are not allowed")
        edge_id = f"edge_{uuid4().hex}"
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO artifact_edges(
                    id, project_id, parent_artifact_id, child_artifact_id, edge_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (edge_id, project_id, parent_artifact_id, child_artifact_id, edge_type, now_iso()),
            )
            row = connection.execute(
                """
                SELECT * FROM artifact_edges
                WHERE parent_artifact_id = ? AND child_artifact_id = ? AND edge_type = ?
                """,
                (parent_artifact_id, child_artifact_id, edge_type),
            ).fetchone()
        return row_to_dict(row)

    def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            if row is None:
                raise RepositoryError(f"Unknown artifact: {artifact_id}")
            artifact = row_to_dict(row)
            version = connection.execute(
                """
                SELECT * FROM artifact_versions
                WHERE artifact_id = ? ORDER BY version_number DESC LIMIT 1
                """,
                (artifact_id,),
            ).fetchone()
        artifact["current_version"] = self._decode_version(version)
        return artifact

    def get_artifact_by_type(self, project_id: str, artifact_type: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE project_id = ? AND artifact_type = ?
                ORDER BY created_at LIMIT 1
                """,
                (project_id, artifact_type),
            ).fetchone()
        if row is None:
            raise RepositoryError(f"Project {project_id} has no artifact of type {artifact_type}")
        return self.get_artifact(row["id"])

    def list_artifacts(self, project_id: str) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id FROM artifacts WHERE project_id = ? ORDER BY created_at", (project_id,)
            ).fetchall()
        return [self.get_artifact(row["id"]) for row in rows]

    def get_version(self, version_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT v.*, a.project_id, a.artifact_type, a.title
                FROM artifact_versions v
                JOIN artifacts a ON a.id = v.artifact_id
                WHERE v.id = ?
                """,
                (version_id,),
            ).fetchone()
        if row is None:
            raise RepositoryError(f"Unknown artifact version: {version_id}")
        return self._decode_version(row)

    def list_versions(self, artifact_id: str) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT v.*, a.project_id, a.artifact_type, a.title
                FROM artifact_versions v
                JOIN artifacts a ON a.id = v.artifact_id
                WHERE artifact_id = ? ORDER BY version_number DESC
                """,
                (artifact_id,),
            ).fetchall()
        return [self._decode_version(row) for row in rows]

    def create_version(
        self,
        artifact_id: str,
        payload: dict[str, Any],
        *,
        status: str = "draft",
        created_by: str = "human",
    ) -> dict[str, Any]:
        if status not in {"draft", "proposed"}:
            raise RepositoryError(
                "New revisions must begin as draft or proposed; approval and locking are separate human decisions"
            )
        timestamp = now_iso()
        version_id = f"ver_{uuid4().hex}"
        with self.database.connect() as connection:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
            if artifact is None:
                raise RepositoryError(f"Unknown artifact: {artifact_id}")
            next_number = int(
                connection.execute(
                    "SELECT COALESCE(MAX(version_number), 0) + 1 FROM artifact_versions WHERE artifact_id = ?",
                    (artifact_id,),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO artifact_versions(
                    id, artifact_id, version_number, status, payload_json,
                    content_hash, created_by, created_at, approved_at, locked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    version_id,
                    artifact_id,
                    next_number,
                    status,
                    canonical_json(payload),
                    content_hash(payload),
                    created_by,
                    timestamp,
                ),
            )
            descendants = self._descendants(connection, artifact_id)
            for descendant_id in descendants:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO impact_records(
                        id, project_id, cause_version_id, affected_artifact_id,
                        classification, resolution_status, reason, created_at
                    ) VALUES (?, ?, ?, ?, 'possibly_stale', 'unresolved', ?, ?)
                    """,
                    (
                        f"impact_{uuid4().hex}",
                        artifact["project_id"],
                        version_id,
                        descendant_id,
                        "An upstream artifact received a new version; review or re-derive this descendant.",
                        timestamp,
                    ),
                )
        return self.get_version(version_id)

    def approve_version(self, version_id: str, *, actor: str, rationale: str) -> dict[str, Any]:
        timestamp = now_iso()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT status FROM artifact_versions WHERE id = ?", (version_id,)
            ).fetchone()
            if row is None:
                raise RepositoryError(f"Unknown artifact version: {version_id}")
            if row["status"] not in {"draft", "proposed"}:
                raise RepositoryError(f"Only draft/proposed versions can be approved, got {row['status']}")
            connection.execute(
                "UPDATE artifact_versions SET status = 'approved', approved_at = ? WHERE id = ?",
                (timestamp, version_id),
            )
            connection.execute(
                """
                INSERT INTO human_decisions(id, version_id, decision, rationale, actor, created_at)
                VALUES (?, ?, 'approved', ?, ?, ?)
                """,
                (f"decision_{uuid4().hex}", version_id, rationale, actor, timestamp),
            )
        return self.get_version(version_id)

    def lock_version(self, version_id: str, *, actor: str, rationale: str) -> dict[str, Any]:
        timestamp = now_iso()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT status FROM artifact_versions WHERE id = ?", (version_id,)
            ).fetchone()
            if row is None:
                raise RepositoryError(f"Unknown artifact version: {version_id}")
            if row["status"] != "approved":
                raise RepositoryError(f"Only approved versions can be locked, got {row['status']}")
            connection.execute(
                "UPDATE artifact_versions SET status = 'locked', locked_at = ? WHERE id = ?",
                (timestamp, version_id),
            )
            connection.execute(
                """
                INSERT INTO human_decisions(id, version_id, decision, rationale, actor, created_at)
                VALUES (?, ?, 'locked', ?, ?, ?)
                """,
                (f"decision_{uuid4().hex}", version_id, rationale, actor, timestamp),
            )
        return self.get_version(version_id)

    def list_lineage(self, project_id: str) -> dict[str, Any]:
        artifacts = self.list_artifacts(project_id)
        with self.database.connect() as connection:
            edges = [
                row_to_dict(row)
                for row in connection.execute(
                    "SELECT * FROM artifact_edges WHERE project_id = ? ORDER BY created_at",
                    (project_id,),
                ).fetchall()
            ]
            impacts = [
                row_to_dict(row)
                for row in connection.execute(
                    """
                    SELECT i.*, a.title AS affected_title, a.artifact_type AS affected_type
                    FROM impact_records i
                    JOIN artifacts a ON a.id = i.affected_artifact_id
                    WHERE i.project_id = ? ORDER BY i.created_at DESC
                    """,
                    (project_id,),
                ).fetchall()
            ]
        return {"nodes": artifacts, "edges": edges, "impacts": impacts}

    def create_skill_run(
        self,
        *,
        project_id: str,
        skill_name: str,
        skill_version: str,
        skill_digest: str,
        input_version_ids: list[str],
        output_version_id: str | None,
        status: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = f"skillrun_{uuid4().hex}"
        timestamp = now_iso()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO skill_runs(
                    id, project_id, skill_name, skill_version, skill_digest,
                    input_version_ids_json, output_version_id, status, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    skill_name,
                    skill_version,
                    skill_digest,
                    canonical_json(input_version_ids),
                    output_version_id,
                    status,
                    canonical_json(details),
                    timestamp,
                ),
            )
        return self.get_skill_run(run_id)

    def get_skill_run(self, run_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM skill_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise RepositoryError(f"Unknown skill run: {run_id}")
        result = row_to_dict(row)
        result["input_version_ids"] = json.loads(result.pop("input_version_ids_json"))
        result["details"] = json.loads(result.pop("details_json"))
        return result

    def create_workflow_run(
        self,
        *,
        project_id: str,
        workflow_name: str,
        workflow_version: str,
        inputs: dict[str, str],
    ) -> dict[str, Any]:
        run_id = f"workflow_{uuid4().hex}"
        timestamp = now_iso()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_runs(
                    id, project_id, workflow_name, workflow_version, status,
                    input_json, output_version_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'running', ?, NULL, ?, ?)
                """,
                (run_id, project_id, workflow_name, workflow_version, canonical_json(inputs), timestamp, timestamp),
            )
        return self.get_workflow_run(run_id)

    def add_workflow_step(
        self,
        workflow_run_id: str,
        step_id: str,
        step_type: str,
        status: str,
        details: dict[str, Any],
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO workflow_run_steps(
                    id, workflow_run_id, step_id, step_type, status, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{workflow_run_id}:{step_id}",
                    workflow_run_id,
                    step_id,
                    step_type,
                    status,
                    canonical_json(details),
                    now_iso(),
                ),
            )

    def update_workflow_run(
        self,
        run_id: str,
        *,
        status: str,
        output_version_id: str | None = None,
    ) -> dict[str, Any]:
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE workflow_runs
                SET status = ?, output_version_id = COALESCE(?, output_version_id), updated_at = ?
                WHERE id = ?
                """,
                (status, output_version_id, now_iso(), run_id),
            )
        return self.get_workflow_run(run_id)

    def get_workflow_run(self, run_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
            steps = connection.execute(
                "SELECT * FROM workflow_run_steps WHERE workflow_run_id = ? ORDER BY created_at",
                (run_id,),
            ).fetchall()
        if row is None:
            raise RepositoryError(f"Unknown workflow run: {run_id}")
        result = row_to_dict(row)
        result["inputs"] = json.loads(result.pop("input_json"))
        result["steps"] = []
        for step in steps:
            item = row_to_dict(step)
            item["details"] = json.loads(item.pop("details_json"))
            result["steps"].append(item)
        return result

    def reset(self) -> None:
        self.database.reset()

    @staticmethod
    def _decode_version(row: Any) -> dict[str, Any]:
        result = row_to_dict(row)
        if not result:
            return result
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    @staticmethod
    def _descendants(connection: Any, artifact_id: str) -> list[str]:
        rows = connection.execute(
            """
            WITH RECURSIVE descendants(id) AS (
                SELECT child_artifact_id
                FROM artifact_edges
                WHERE parent_artifact_id = ?
                UNION
                SELECT e.child_artifact_id
                FROM artifact_edges e
                JOIN descendants d ON e.parent_artifact_id = d.id
            )
            SELECT DISTINCT id FROM descendants
            """,
            (artifact_id,),
        ).fetchall()
        return [row["id"] for row in rows]
