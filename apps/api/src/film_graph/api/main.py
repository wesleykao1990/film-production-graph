"""Thin FastAPI commands/queries for the M01 core."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from film_graph.application import (
    ApproveAssetCommand,
    BindProjectSkillCommand,
    BulkResolveImpactsCommand,
    CreateArtifactCommand,
    CreateAssetCommand,
    CreateEdgeCommand,
    CreateProjectCommand,
    CreateProjectEventCommand,
    CreateProviderPolicyCommand,
    CreateRightsCommand,
    CreateRunCommand,
    FilmGraphApplicationService,
    ResolveImpactCommand,
    ReviseArtifactCommand,
    TransitionVersionCommand,
)
from film_graph.application.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from film_graph.domain import (
    ActorRef,
    ActorType,
    ImpactClassification,
    ImpactResolutionStatus,
    LifecycleStatus,
    RightsRecord,
    RightsSourceType,
    RightsStatus,
)
from film_graph.persistence import PostgresGraphRepository
from film_graph.persistence.errors import PersistenceUnavailable
from film_graph.skills import SkillError, SkillRegistry
from pydantic import BaseModel, ConfigDict, Field

SERVICE_NAME = "film-production-graph-api"
SERVICE_VERSION = "0.1.0"


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActorRequest(_Request):
    actor_type: ActorType
    actor_id: str = Field(min_length=1)
    display_name: str | None = None

    def domain(self) -> ActorRef:
        return ActorRef(self.actor_type, self.actor_id, self.display_name)


class ProjectRequest(_Request):
    name: str = Field(min_length=1)
    project_id: UUID | None = None


class ArtifactRequest(_Request):
    artifact_type: str = Field(min_length=1)
    logical_key: str = Field(min_length=1)
    payload: dict[str, Any]
    actor: ActorRequest
    schema_version: str = "1.0"
    provenance: dict[str, Any] | None = None


class RevisionRequest(_Request):
    payload: dict[str, Any]
    actor: ActorRequest
    expected_current_revision: int = Field(ge=1)
    schema_version: str | None = None
    provenance: dict[str, Any] | None = None


class TransitionRequest(_Request):
    target_status: LifecycleStatus
    actor: ActorRequest
    expected_current_revision: int = Field(ge=1)
    rationale: str | None = None


class LifecycleRequest(_Request):
    actor: ActorRequest
    expected_current_revision: int = Field(ge=1)
    rationale: str | None = None


class EdgeRequest(_Request):
    project_id: UUID
    from_version_id: UUID
    to_version_id: UUID
    edge_type: str = "DERIVED_FROM"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImpactResolutionRequest(_Request):
    classification: ImpactClassification
    resolution_status: ImpactResolutionStatus
    actor: ActorRequest


class ImpactValidationRequest(_Request):
    contradicted: bool
    finding: str | None = None
    actor: ActorRequest


class AssetRequest(_Request):
    asset_type: str = Field(min_length=1)
    logical_key: str = Field(min_length=1)
    payload: dict[str, Any]
    actor: ActorRequest


class RightsRequest(_Request):
    subject_ref: str = Field(min_length=1)
    status: RightsStatus
    source_type: RightsSourceType
    holder: str = Field(min_length=1)
    permitted_uses: list[str] = Field(min_length=1)
    territories: list[str] = Field(min_length=1)
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    license_or_permission: str | None = None
    starts_at: str | None = None
    expires_at: str | None = None
    attribution: str | None = None
    evidence_asset_refs: list[str] = Field(default_factory=list)
    consent_record_refs: list[str] = Field(default_factory=list)
    provider_policy_ref: str | None = None
    notes: list[str] = Field(default_factory=list)
    actor: ActorRequest


class RunRequest(_Request):
    actor: ActorRequest
    provenance: dict[str, Any] = Field(default_factory=dict)
    model_alias: str | None = None
    resolved_provider: str | None = None
    resolved_model: str | None = None
    disposition: str = "completed"


class SkillReloadRequest(_Request):
    actor: ActorRequest


class SkillBindingRequest(_Request):
    agent_ref: str = Field(min_length=1)
    skill_name: str = Field(min_length=1)
    actor: ActorRequest


class SkillFakeRunRequest(_Request):
    agent_ref: str = Field(min_length=1)
    actor: ActorRequest


class ProviderPolicyRequest(_Request):
    provider: str = Field(min_length=1)
    captured_at: str
    commercial_use_status: str
    retention_training_status: str
    allowed_for_project: bool
    actor: ActorRequest
    model_or_service: str | None = None
    source_url_or_document_ref: str | None = None
    voice_likeness_constraints: list[str] = Field(default_factory=list)
    distribution_constraints: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    provider_policy_id: UUID | None = None


def _parse_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _parse_optional_time(raw: str | None) -> datetime | None:
    return _parse_time(raw) if raw else None


def _health_payload() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


def _configured_skill_registry() -> SkillRegistry | None:
    raw_repository = os.getenv("FPG_REPOSITORY_ROOT")
    if not raw_repository:
        return None
    repository = Path(raw_repository)
    raw_roots = os.getenv("FPG_SKILL_ROOTS", "skills")
    roots = [Path(item.strip()) for item in raw_roots.split(",") if item.strip()]
    registry = SkillRegistry(
        repository_root=repository,
        skill_roots=roots,
        lock_path=Path(os.getenv("FPG_SKILLS_LOCK", "skills.lock")),
    )
    registry.reload()
    return registry


def create_app(
    service: FilmGraphApplicationService | None = None,
    skill_registry: SkillRegistry | None = None,
) -> FastAPI:
    if service is None and os.getenv("FPG_DATABASE_URL"):
        service = FilmGraphApplicationService(PostgresGraphRepository())
    if skill_registry is None:
        skill_registry = _configured_skill_registry()
    application = FastAPI(
        title="Film Production Graph API",
        version=SERVICE_VERSION,
        description=(
            "M01 Artifact, Lineage, Impact, Rights, provenance, and M02 skills API; "
            "no provider calls are made."
        ),
    )

    @application.get("/", tags=["diagnostics"])
    def root() -> dict[str, str]:
        return _health_payload()

    @application.get("/health", tags=["diagnostics"])
    @application.get("/api/health", tags=["diagnostics"])
    def health() -> dict[str, str]:
        return _health_payload()

    def _service() -> FilmGraphApplicationService:
        if service is None:
            raise HTTPException(status_code=503, detail="Postgres persistence is not configured")
        return service

    def _skills() -> SkillRegistry:
        if skill_registry is None:
            raise HTTPException(status_code=503, detail="repository skills are not configured")
        return skill_registry

    def _error(exc: Exception) -> HTTPException:
        if isinstance(exc, PersistenceUnavailable):
            return HTTPException(status_code=503, detail=str(exc))
        if isinstance(exc, NotFoundError):
            return HTTPException(status_code=404, detail=str(exc))
        if isinstance(exc, (ConflictError, ValidationError)):
            return HTTPException(
                status_code=409 if isinstance(exc, ConflictError) else 422, detail=str(exc)
            )
        if isinstance(exc, (TypeError, ValueError)):
            return HTTPException(status_code=422, detail=str(exc))
        if isinstance(exc, SkillError):
            return HTTPException(status_code=409, detail=str(exc))
        return HTTPException(status_code=400, detail=str(exc))

    @application.get("/api/skills", tags=["skills"])
    def list_skills() -> dict[str, Any]:
        try:
            snapshot = _skills().snapshot
            return {
                "snapshot_hash": snapshot.snapshot_hash,
                "skills": [skill.as_dict() for skill in snapshot.list()],
            }
        except SkillError as exc:
            raise _error(exc) from exc

    @application.post("/api/skills/reload", tags=["skills"])
    def reload_skills(request: SkillReloadRequest) -> dict[str, Any]:
        try:
            request.actor.domain().require_human()
            snapshot = _skills().reload()
            return {
                "snapshot_hash": snapshot.snapshot_hash,
                "skills": [skill.as_dict() for skill in snapshot.list()],
            }
        except (SkillError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post(
        "/api/projects/{project_id}/skill-bindings", tags=["skills"], status_code=201
    )
    def bind_project_skill(
        project_id: UUID, request: SkillBindingRequest
    ) -> dict[str, Any]:
        try:
            snapshot = _skills().snapshot
            skill = snapshot.get(request.skill_name)
            ref = skill.locked_ref
            binding = _service().bind_project_skill(
                BindProjectSkillCommand(
                    project_id=project_id,
                    agent_ref=request.agent_ref,
                    skill_name=ref.name,
                    source_path=ref.source_path,
                    source_commit=ref.source_commit,
                    content_hash=ref.content_hash,
                    metadata_version=ref.metadata_version,
                    snapshot_hash=snapshot.snapshot_hash,
                    actor=request.actor.domain(),
                )
            )
            return binding.as_dict()
        except (ApplicationError, SkillError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/projects/{project_id}/skill-bindings", tags=["skills"])
    def list_project_skill_bindings(
        project_id: UUID, agent_ref: str | None = None
    ) -> list[dict[str, Any]]:
        try:
            return [
                binding.as_dict()
                for binding in _service().list_project_skill_bindings(
                    project_id, agent_ref=agent_ref
                )
            ]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post(
        "/api/projects/{project_id}/skills/{skill_name}/fake-run",
        tags=["skills"],
        status_code=201,
    )
    def fake_run_skill(
        project_id: UUID, skill_name: str, request: SkillFakeRunRequest
    ) -> dict[str, Any]:
        try:
            snapshot = _skills().snapshot
            skill = snapshot.get(skill_name)
            binding = _service().get_project_skill_binding(
                project_id, request.agent_ref, skill_name
            )
            exact_ref = skill.locked_ref.as_dict()
            bound_ref = {
                "name": binding.skill_name,
                "source_path": binding.source_path,
                "source_commit": binding.source_commit,
                "content_hash": binding.content_hash,
                "metadata_version": binding.metadata_version,
            }
            if binding.snapshot_hash != snapshot.snapshot_hash or bound_ref != exact_ref:
                raise ConflictError("skill binding does not match the current exact snapshot")
            provenance = {
                "mode": "fake_no_provider",
                "agent_ref": request.agent_ref,
                "resolved_skill_set_hash": snapshot.snapshot_hash,
                "skills": [exact_ref],
            }
            run = _service().create_run(
                CreateRunCommand(
                    project_id=project_id,
                    actor=request.actor.domain(),
                    provenance=provenance,
                    disposition="completed",
                )
            )
            return {
                "run_id": str(run.id),
                "project_id": str(run.project_id),
                "disposition": run.disposition,
                "provenance": provenance,
            }
        except (ApplicationError, SkillError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    def _artifact_response(identity: Any, version: Any) -> dict[str, Any]:
        return {
            **version.as_dict(),
            "artifact_type": identity.artifact_type,
            "logical_key": identity.logical_key,
        }

    @application.get("/api/projects", tags=["projects"])
    def list_projects() -> list[dict[str, Any]]:
        try:
            return [
                {
                    "project_id": str(project.id),
                    "name": project.name,
                    "created_at": project.created_at.isoformat(),
                }
                for project in _service().list_projects()
            ]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/projects", tags=["projects"], status_code=201)
    def create_project(request: ProjectRequest) -> dict[str, Any]:
        try:
            project = _service().create_project(
                CreateProjectCommand(name=request.name, project_id=request.project_id)
            )
            return {
                "project_id": str(project.id),
                "name": project.name,
                "created_at": project.created_at.isoformat(),
            }
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/projects/{project_id}/artifacts", tags=["artifacts"])
    def list_artifacts(project_id: UUID) -> list[dict[str, Any]]:
        try:
            return [
                {
                    **version.as_dict(),
                    "logical_key": identity.logical_key,
                    "artifact_type": identity.artifact_type,
                }
                for identity, version in _service().list_artifacts(project_id)
            ]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/projects/{project_id}/artifacts", tags=["artifacts"], status_code=201)
    def create_artifact(project_id: UUID, request: ArtifactRequest) -> dict[str, Any]:
        try:
            version = _service().create_artifact(
                CreateArtifactCommand(
                    project_id=project_id,
                    artifact_type=request.artifact_type,
                    logical_key=request.logical_key,
                    payload=request.payload,
                    actor=request.actor.domain(),
                    schema_version=request.schema_version,
                    provenance=request.provenance,
                )
            )
            identity, created = _service().get_version(version.id)
            return _artifact_response(identity, created)
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/artifacts/{artifact_id}", tags=["artifacts"])
    def get_artifact(artifact_id: UUID) -> dict[str, Any]:
        try:
            identity, version = _service().get_artifact(artifact_id)
            return _artifact_response(identity, version)
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/artifacts/{artifact_id}/revisions", tags=["artifacts"], status_code=201)
    @application.post("/api/artifacts/{artifact_id}/versions", tags=["artifacts"], status_code=201)
    def revise_artifact(artifact_id: UUID, request: RevisionRequest) -> dict[str, Any]:
        try:
            version = _service().revise_artifact(
                ReviseArtifactCommand(
                    artifact_id=artifact_id,
                    payload=request.payload,
                    actor=request.actor.domain(),
                    expected_current_revision=request.expected_current_revision,
                    schema_version=request.schema_version,
                    provenance=request.provenance,
                )
            )
            identity, created = _service().get_version(version.id)
            return _artifact_response(identity, created)
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/artifacts/{artifact_id}/versions", tags=["artifacts"])
    def list_versions(artifact_id: UUID) -> list[dict[str, Any]]:
        try:
            identity, _ = _service().get_artifact(artifact_id)
            versions = _service().list_versions(artifact_id)
            return [_artifact_response(identity, version) for version in versions]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/versions/{version_id}", tags=["artifacts"])
    def get_version(version_id: UUID) -> dict[str, Any]:
        try:
            identity, version = _service().get_version(version_id)
            return _artifact_response(identity, version)
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/versions/{version_id}/transition", tags=["artifacts"])
    def transition_version(version_id: UUID, request: TransitionRequest) -> dict[str, Any]:
        try:
            version = _service().transition_version(
                TransitionVersionCommand(
                    version_id,
                    request.target_status,
                    request.actor.domain(),
                    request.expected_current_revision,
                    request.rationale,
                )
            )
            identity, updated = _service().get_version(version.id)
            return _artifact_response(identity, updated)
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/versions/{version_id}/approve", tags=["artifacts"])
    def approve_version(version_id: UUID, request: LifecycleRequest) -> dict[str, Any]:
        return transition_version(
            version_id,
            TransitionRequest(
                target_status=LifecycleStatus.APPROVED,
                actor=request.actor,
                expected_current_revision=request.expected_current_revision,
                rationale=request.rationale,
            ),
        )

    @application.post("/api/versions/{version_id}/lock", tags=["artifacts"])
    def lock_version(version_id: UUID, request: LifecycleRequest) -> dict[str, Any]:
        return transition_version(
            version_id,
            TransitionRequest(
                target_status=LifecycleStatus.LOCKED,
                actor=request.actor,
                expected_current_revision=request.expected_current_revision,
                rationale=request.rationale,
            ),
        )

    def _lifecycle_convenience(
        version_id: UUID, request: LifecycleRequest, target: LifecycleStatus
    ) -> dict[str, Any]:
        return transition_version(
            version_id,
            TransitionRequest(
                target_status=target,
                actor=request.actor,
                expected_current_revision=request.expected_current_revision,
                rationale=request.rationale,
            ),
        )

    @application.post("/api/versions/{version_id}/validate", tags=["artifacts"])
    def validate_version(version_id: UUID, request: LifecycleRequest) -> dict[str, Any]:
        return _lifecycle_convenience(version_id, request, LifecycleStatus.VALIDATED)

    @application.post("/api/versions/{version_id}/review", tags=["artifacts"])
    def review_version(version_id: UUID, request: LifecycleRequest) -> dict[str, Any]:
        return _lifecycle_convenience(version_id, request, LifecycleStatus.HUMAN_REVIEW)

    @application.post("/api/versions/{version_id}/reject", tags=["artifacts"])
    def reject_version(version_id: UUID, request: LifecycleRequest) -> dict[str, Any]:
        return _lifecycle_convenience(version_id, request, LifecycleStatus.REJECTED)

    @application.post("/api/edges", tags=["lineage"], status_code=201)
    def create_edge(request: EdgeRequest) -> dict[str, Any]:
        try:
            return (
                _service()
                .create_edge(
                    CreateEdgeCommand(
                        project_id=request.project_id,
                        from_version_id=request.from_version_id,
                        to_version_id=request.to_version_id,
                        edge_type=request.edge_type,
                        metadata=request.metadata,
                    )
                )
                .as_dict()
            )
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/versions/{version_id}/lineage", tags=["lineage"])
    def lineage(version_id: UUID, direction: str = "downstream") -> dict[str, Any]:
        try:
            return {
                "direction": direction,
                "nodes": [
                    item.as_dict() for item in _service().lineage(version_id, direction=direction)
                ],
            }
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/projects/{project_id}/impacts", tags=["impact"])
    def list_impacts(project_id: UUID, unresolved_only: bool = False) -> list[dict[str, Any]]:
        try:
            return [
                item.as_dict()
                for item in _service().list_impacts(project_id, unresolved_only=unresolved_only)
            ]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/impacts/{impact_id}/resolve", tags=["impact"])
    def resolve_impact(impact_id: UUID, request: ImpactResolutionRequest) -> dict[str, Any]:
        try:
            return (
                _service()
                .resolve_impact(
                    ResolveImpactCommand(
                        impact_id=impact_id,
                        classification=request.classification,
                        resolution_status=request.resolution_status,
                        actor=request.actor.domain(),
                    )
                )
                .as_dict()
            )
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/impacts/{impact_id}/validate", tags=["impact"])
    def validate_impact(impact_id: UUID, request: ImpactValidationRequest) -> dict[str, Any]:
        try:
            return (
                _service()
                .validate_impact(
                    impact_id,
                    contradicted=request.contradicted,
                    finding=request.finding,
                    actor=request.actor.domain(),
                )
                .as_dict()
            )
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/impacts/bulk-resolve", tags=["impact"])
    def bulk_resolve_impacts(request: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            actor = ActorRef(ActorType(str(request["actor_type"])), str(request["actor_id"]))
            command = BulkResolveImpactsCommand.from_iterable(
                (UUID(str(value)) for value in request["impact_ids"]),
                classification=ImpactClassification(str(request["classification"])),
                resolution_status=ImpactResolutionStatus(str(request["resolution_status"])),
                actor=actor,
            )
            return [item.as_dict() for item in _service().bulk_resolve_impacts(command)]
        except (ApplicationError, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ApplicationError):
                raise _error(exc) from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @application.post("/api/projects/{project_id}/assets", tags=["rights"], status_code=201)
    def create_asset(project_id: UUID, request: AssetRequest) -> dict[str, Any]:
        try:
            asset = _service().create_asset(
                CreateAssetCommand(
                    project_id,
                    request.asset_type,
                    request.logical_key,
                    request.payload,
                    request.actor.domain(),
                )
            )
            return {
                "asset_id": str(asset.id),
                "project_id": str(asset.project_id),
                "lifecycle_status": asset.lifecycle_status.value,
            }
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/projects/{project_id}/rights", tags=["rights"], status_code=201)
    def create_rights(project_id: UUID, request: RightsRequest) -> dict[str, Any]:
        try:
            record = RightsRecord.create(
                project_id=project_id,
                subject_ref=request.subject_ref,
                status=request.status,
                source_type=request.source_type,
                holder=request.holder,
                permitted_uses=request.permitted_uses,
                territories=request.territories,
                reviewed_by=request.reviewed_by,
                reviewed_at=_parse_optional_time(request.reviewed_at),
                license_or_permission=request.license_or_permission,
                starts_at=_parse_optional_time(request.starts_at),
                expires_at=_parse_optional_time(request.expires_at),
                attribution=request.attribution,
                evidence_asset_refs=tuple(request.evidence_asset_refs),
                consent_record_refs=tuple(request.consent_record_refs),
                provider_policy_ref=request.provider_policy_ref,
                notes=tuple(request.notes),
            )
            return (
                _service()
                .create_rights(CreateRightsCommand(record, request.actor.domain()))
                .as_dict()
            )
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/assets/{asset_id}/approve", tags=["rights"])
    def approve_asset(asset_id: UUID, request: ActorRequest) -> dict[str, Any]:
        try:
            asset = _service().approve_asset(ApproveAssetCommand(asset_id, request.domain()))
            return {"asset_id": str(asset.id), "lifecycle_status": asset.lifecycle_status.value}
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/projects/{project_id}/runs", tags=["runs"], status_code=201)
    def create_run(project_id: UUID, request: RunRequest) -> dict[str, Any]:
        try:
            run = _service().create_run(
                CreateRunCommand(
                    project_id=project_id,
                    actor=request.actor.domain(),
                    provenance=request.provenance,
                    model_alias=request.model_alias,
                    resolved_provider=request.resolved_provider,
                    resolved_model=request.resolved_model,
                    disposition=request.disposition,
                )
            )
            return {
                "run_id": str(run.id),
                "project_id": str(run.project_id),
                "disposition": run.disposition,
            }
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post(
        "/api/projects/{project_id}/provider-policies", tags=["provenance"], status_code=201
    )
    def create_provider_policy(project_id: UUID, request: ProviderPolicyRequest) -> dict[str, Any]:
        try:
            policy = _service().create_provider_policy(
                CreateProviderPolicyCommand(
                    project_id=project_id,
                    provider=request.provider,
                    captured_at=_parse_time(request.captured_at),
                    commercial_use_status=request.commercial_use_status,
                    retention_training_status=request.retention_training_status,
                    allowed_for_project=request.allowed_for_project,
                    actor=request.actor.domain(),
                    model_or_service=request.model_or_service,
                    source_url_or_document_ref=request.source_url_or_document_ref,
                    voice_likeness_constraints=tuple(request.voice_likeness_constraints),
                    distribution_constraints=tuple(request.distribution_constraints),
                    block_reasons=tuple(request.block_reasons),
                    policy_id=request.provider_policy_id,
                )
            )
            return policy.as_dict()
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/projects/{project_id}/provider-policies", tags=["provenance"])
    def list_provider_policies(project_id: UUID) -> list[dict[str, Any]]:
        try:
            return [
                item.as_dict() for item in _service().list_provider_policies(project_id)
            ]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/projects/{project_id}/decisions", tags=["provenance"])
    def list_decisions(
        project_id: UUID, subject_ref: str | None = None
    ) -> list[dict[str, Any]]:
        try:
            return [
                item.as_dict()
                for item in _service().list_human_decisions(
                    project_id, subject_ref=subject_ref
                )
            ]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.get("/api/projects/{project_id}/events", tags=["provenance"])
    def list_events(project_id: UUID) -> list[dict[str, Any]]:
        try:
            return [item.as_dict() for item in _service().list_project_events(project_id)]
        except (ApplicationError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    @application.post("/api/projects/{project_id}/events", tags=["provenance"], status_code=201)
    def create_event(project_id: UUID, request: dict[str, Any]) -> dict[str, Any]:
        try:
            actor = ActorRef(ActorType(str(request["actor_type"])), str(request["actor_id"]))
            event = _service().create_project_event(
                CreateProjectEventCommand(
                    project_id=project_id,
                    event_type=str(request["event_type"]),
                    actor=actor,
                    subject_ref=request.get("subject_ref"),
                    payload=request.get("payload") or {},
                )
            )
            return event.as_dict()
        except (ApplicationError, KeyError, TypeError, ValueError) as exc:
            raise _error(exc) from exc

    return application


app = create_app()
