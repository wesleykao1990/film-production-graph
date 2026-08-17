from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_versions (
    id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft', 'proposed', 'approved', 'locked', 'rejected', 'deprecated')),
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    approved_at TEXT,
    locked_at TEXT,
    UNIQUE(artifact_id, version_number)
);

CREATE TABLE IF NOT EXISTS artifact_edges (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    child_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(parent_artifact_id, child_artifact_id, edge_type)
);

CREATE TABLE IF NOT EXISTS impact_records (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cause_version_id TEXT NOT NULL REFERENCES artifact_versions(id) ON DELETE CASCADE,
    affected_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    classification TEXT NOT NULL CHECK(classification IN ('possibly_stale', 'contradicted', 'reviewed_valid', 'rederive_requested', 'resolved')),
    resolution_status TEXT NOT NULL DEFAULT 'unresolved',
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(cause_version_id, affected_artifact_id)
);

CREATE TABLE IF NOT EXISTS human_decisions (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL REFERENCES artifact_versions(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    skill_digest TEXT NOT NULL,
    input_version_ids_json TEXT NOT NULL,
    output_version_id TEXT REFERENCES artifact_versions(id),
    status TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    workflow_name TEXT NOT NULL,
    workflow_version TEXT NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL,
    output_version_id TEXT REFERENCES artifact_versions(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_run_steps (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_id TEXT NOT NULL,
    step_type TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(workflow_run_id, step_id)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_versions_artifact ON artifact_versions(artifact_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_edges_parent ON artifact_edges(parent_artifact_id);
CREATE INDEX IF NOT EXISTS idx_edges_child ON artifact_edges(child_artifact_id);
CREATE INDEX IF NOT EXISTS idx_impacts_project ON impact_records(project_id, resolution_status);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
        self.initialize()
