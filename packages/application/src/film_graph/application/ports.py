"""Application ports kept independent of web and persistence frameworks."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from film_graph.contracts.provider import MediaRequest, MediaResponse, ModelRequest, ModelResponse
from film_graph.domain import (
    ArtifactEdge,
    ArtifactIdentity,
    ArtifactVersion,
    Asset,
    AssetVersion,
    HumanDecision,
    ImpactRecord,
    Project,
    ProjectEvent,
    ProjectSkillBinding,
    ProviderPolicy,
    RightsRecord,
    RunRecord,
)


class ModelRunner(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...


class MediaRunner(Protocol):
    def generate(self, request: MediaRequest) -> MediaResponse: ...


class GraphRepository(Protocol):
    """The narrow persistence port used by application commands."""

    def create_project(self, project: Project) -> Project: ...

    def list_projects(self) -> list[Project]: ...

    def get_project(self, project_id: UUID) -> Project | None: ...

    def create_project_skill_binding(self, binding: ProjectSkillBinding) -> ProjectSkillBinding: ...

    def get_project_skill_binding(
        self, project_id: UUID, agent_ref: str, skill_name: str
    ) -> ProjectSkillBinding | None: ...

    def list_project_skill_bindings(
        self, project_id: UUID, *, agent_ref: str | None = None
    ) -> list[ProjectSkillBinding]: ...

    def create_artifact(
        self, identity: ArtifactIdentity, version: ArtifactVersion
    ) -> tuple[ArtifactIdentity, ArtifactVersion]: ...

    def get_identity(self, artifact_id: UUID) -> ArtifactIdentity | None: ...

    def get_version(self, version_id: UUID) -> ArtifactVersion | None: ...

    def current_version(self, artifact_id: UUID) -> ArtifactVersion | None: ...

    def list_versions(self, artifact_id: UUID) -> list[ArtifactVersion]: ...

    def list_artifacts(
        self, project_id: UUID
    ) -> list[tuple[ArtifactIdentity, ArtifactVersion]]: ...

    def revise_artifact(
        self,
        identity: ArtifactIdentity,
        previous: ArtifactVersion,
        version: ArtifactVersion,
        *,
        expected_current_revision: int,
    ) -> tuple[ArtifactIdentity, ArtifactVersion]: ...

    def transition_version(
        self,
        version_id: UUID,
        target: Any,
        actor: Any,
        *,
        expected_current_revision: int,
        rationale: str | None,
    ) -> ArtifactVersion: ...

    def create_edge(self, edge: ArtifactEdge) -> ArtifactEdge: ...

    def lineage(self, version_id: UUID, *, direction: str) -> list[ArtifactVersion]: ...

    def list_impacts(
        self, project_id: UUID, *, unresolved_only: bool = False
    ) -> list[ImpactRecord]: ...

    def resolve_impact(
        self,
        impact_id: UUID,
        classification: Any,
        resolution_status: Any,
        actor: Any,
    ) -> ImpactRecord: ...

    def validate_impact(
        self, impact_id: UUID, *, contradicted: bool, finding: str | None, actor: Any
    ) -> ImpactRecord: ...

    def create_asset(self, asset: Asset, version: AssetVersion) -> tuple[Asset, AssetVersion]: ...

    def create_rights(self, record: RightsRecord, actor: Any) -> RightsRecord: ...

    def approve_asset(self, asset_id: UUID, actor: Any) -> Asset: ...

    def create_run(self, run: RunRecord) -> RunRecord: ...

    def create_provider_policy(self, policy: ProviderPolicy) -> ProviderPolicy: ...

    def list_provider_policies(self, project_id: UUID) -> list[ProviderPolicy]: ...

    def create_project_event(self, event: ProjectEvent) -> ProjectEvent: ...

    def list_project_events(self, project_id: UUID) -> list[ProjectEvent]: ...

    def list_human_decisions(
        self, project_id: UUID, *, subject_ref: str | None = None
    ) -> list[HumanDecision]: ...
