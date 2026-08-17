from __future__ import annotations

import copy
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent import MockAgentProvider
from .config import Settings
from .db import Database
from .models import (
    DecisionRequest,
    SkillRunRequest,
    VersionCreateRequest,
    WorkflowApprovalRequest,
    WorkflowRunRequest,
)
from .repository import Repository, RepositoryError
from .seed import seed_if_empty
from .services import FilmGraphService, ServiceError
from .skills import SkillRegistry
from .workflows import WorkflowRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.default()
    database = Database(settings.db_path)
    repository = Repository(database)
    skills = SkillRegistry(settings.skill_root)
    workflows = WorkflowRegistry(settings.workflow_root)
    service = FilmGraphService(repository, skills, workflows, MockAgentProvider())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.initialize()
        seed_if_empty(repository, settings.seed_path)
        skills.load()
        workflows.load()
        yield

    app = FastAPI(
        title="Film Production Graph Reference Prototype",
        version="0.1.0",
        description=(
            "A local, deterministic reference prototype. It demonstrates immutable artifact versions, "
            "lineage, impact records, repository skill hashing, typed proposals, and human approval."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repository = repository
    app.state.skills = skills
    app.state.workflows = workflows
    app.state.service = service

    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(settings.static_dir / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "database": str(settings.db_path),
            "projects": repository.project_count(),
            "skills": len(skills.list()),
            "workflows": len(workflows.list()),
            "mode": "deterministic-reference-prototype",
        }

    @app.get("/api/projects")
    def list_projects() -> list[dict[str, Any]]:
        return repository.list_projects()

    @app.get("/api/projects/{project_id}/artifacts")
    def list_artifacts(project_id: str) -> list[dict[str, Any]]:
        try:
            return repository.list_artifacts(project_id)
        except RepositoryError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/projects/{project_id}/lineage")
    def lineage(project_id: str) -> dict[str, Any]:
        try:
            repository.get_project(project_id)
            return repository.list_lineage(project_id)
        except RepositoryError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/artifacts/{artifact_id}")
    def get_artifact(artifact_id: str) -> dict[str, Any]:
        try:
            artifact = repository.get_artifact(artifact_id)
            artifact["versions"] = repository.list_versions(artifact_id)
            return artifact
        except RepositoryError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/artifacts/{artifact_id}/versions")
    def create_version(artifact_id: str, request: VersionCreateRequest) -> dict[str, Any]:
        try:
            return repository.create_version(
                artifact_id,
                request.payload,
                status=request.status,
                created_by=request.created_by,
            )
        except RepositoryError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/versions/{version_id}/approve")
    def approve(version_id: str, request: DecisionRequest) -> dict[str, Any]:
        try:
            return repository.approve_version(
                version_id, actor=request.actor, rationale=request.rationale
            )
        except RepositoryError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/versions/{version_id}/lock")
    def lock(version_id: str, request: DecisionRequest) -> dict[str, Any]:
        try:
            return repository.lock_version(
                version_id, actor=request.actor, rationale=request.rationale
            )
        except RepositoryError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/skills")
    def list_skills() -> list[dict[str, Any]]:
        return [skill.public_dict() for skill in skills.list()]

    @app.post("/api/skills/{skill_name}/run")
    def run_skill(skill_name: str, request: SkillRunRequest) -> dict[str, Any]:
        try:
            return service.run_skill(
                project_id=request.project_id,
                skill_name=skill_name,
                input_version_ids=request.input_version_ids,
            )
        except ServiceError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/workflows")
    def list_workflows() -> list[dict[str, Any]]:
        return [workflow.public_dict() for workflow in workflows.list()]

    @app.post("/api/workflows/{workflow_name}/run")
    def run_workflow(workflow_name: str, request: WorkflowRunRequest) -> dict[str, Any]:
        try:
            return service.run_workflow(
                project_id=request.project_id,
                workflow_name=workflow_name,
                inputs=request.inputs,
            )
        except ServiceError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/workflow-runs/{run_id}")
    def get_workflow_run(run_id: str) -> dict[str, Any]:
        try:
            return repository.get_workflow_run(run_id)
        except RepositoryError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/workflow-runs/{run_id}/approve")
    def approve_workflow(run_id: str, request: WorkflowApprovalRequest) -> dict[str, Any]:
        try:
            return service.approve_workflow(
                run_id, actor=request.actor, rationale=request.rationale
            )
        except ServiceError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/demo/revise-scene-contract")
    def revise_scene_contract() -> dict[str, Any]:
        project_id = "project_blue_pen"
        try:
            artifact = repository.get_artifact_by_type(project_id, "scene_contract")
            payload = copy.deepcopy(artifact["current_version"]["payload"])
            payload["revision_note"] = "Prototype revision: strengthen the prohibition on explicit confession."
            forbidden = list(payload.get("forbidden", []))
            if "direct confession before the turn" not in forbidden:
                forbidden.append("direct confession before the turn")
            payload["forbidden"] = forbidden
            version = repository.create_version(
                artifact["id"], payload, status="draft", created_by="prototype-user"
            )
            return {"version": version, "lineage": repository.list_lineage(project_id)}
        except RepositoryError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/demo/reset")
    def reset_demo() -> dict[str, Any]:
        repository.reset()
        seed_if_empty(repository, settings.seed_path)
        skills.load()
        workflows.load()
        return {"status": "reset", "project_id": "project_blue_pen"}

    return app


app = create_app()
