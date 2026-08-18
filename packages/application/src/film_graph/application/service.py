"""Thin command/query application service for M01."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from film_graph.domain import (
    ActorRef,
    ArtifactEdge,
    ArtifactIdentity,
    ArtifactVersion,
    Asset,
    AssetVersion,
    HumanDecision,
    ImpactRecord,
    LifecycleStatus,
    Project,
    ProjectEvent,
    ProjectSkillBinding,
    ProviderPolicy,
    RightsRecord,
    RightsStatus,
    RunRecord,
    content_hash,
)

from .commands import (
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
    ResolveImpactCommand,
    ReviseArtifactCommand,
    TransitionVersionCommand,
)
from .errors import NotFoundError, ValidationError
from .ports import GraphRepository


class FilmGraphApplicationService:
    """Own business commands; adapters only persist/serialize their result."""

    def __init__(self, repository: GraphRepository) -> None:
        self.repository = repository

    def create_project(self, command: CreateProjectCommand) -> Project:
        return self.repository.create_project(
            Project.create(command.name, project_id=command.project_id)
        )

    def list_projects(self) -> list[Project]:
        return self.repository.list_projects()

    def bind_project_skill(self, command: BindProjectSkillCommand) -> ProjectSkillBinding:
        """Persist an exact, human-attested skill reference for a project agent."""

        if self.repository.get_project(command.project_id) is None:
            raise NotFoundError(f"project not found: {command.project_id}")
        command.actor.require_human()
        try:
            binding = ProjectSkillBinding(
                id=command.binding_id or uuid4(),
                project_id=command.project_id,
                agent_ref=command.agent_ref,
                skill_name=command.skill_name,
                source_path=command.source_path,
                source_commit=command.source_commit,
                content_hash=command.content_hash,
                metadata_version=command.metadata_version,
                snapshot_hash=command.snapshot_hash,
                bound_by=command.actor,
                created_at=command.created_at or datetime.now(UTC),
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return self.repository.create_project_skill_binding(binding)

    def get_project_skill_binding(
        self, project_id: Any, agent_ref: str, skill_name: str
    ) -> ProjectSkillBinding:
        if self.repository.get_project(project_id) is None:
            raise NotFoundError(f"project not found: {project_id}")
        binding = self.repository.get_project_skill_binding(project_id, agent_ref, skill_name)
        if binding is None:
            raise NotFoundError(
                "skill binding not found for project "
                f"{project_id}, agent {agent_ref}, skill {skill_name}"
            )
        return binding

    def list_project_skill_bindings(
        self, project_id: Any, *, agent_ref: str | None = None
    ) -> list[ProjectSkillBinding]:
        if self.repository.get_project(project_id) is None:
            raise NotFoundError(f"project not found: {project_id}")
        return self.repository.list_project_skill_bindings(project_id, agent_ref=agent_ref)

    def create_artifact(self, command: CreateArtifactCommand) -> ArtifactVersion:
        if command.actor.actor_type.value not in {"user", "agent", "workflow", "system", "import"}:
            raise ValidationError("unsupported actor type")
        if self.repository.get_project(command.project_id) is None:
            raise NotFoundError(f"project not found: {command.project_id}")
        try:
            identity = ArtifactIdentity(
                id=uuid4(),
                project_id=command.project_id,
                artifact_type=command.artifact_type,
                logical_key=command.logical_key,
            )
            version = ArtifactVersion.create(
                artifact_id=identity.id,
                project_id=command.project_id,
                payload=command.payload,
                created_by=command.actor,
                schema_version=command.schema_version,
                provenance=command.provenance,
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return self.repository.create_artifact(identity, version)[1]

    def get_artifact(self, artifact_id: Any) -> tuple[ArtifactIdentity, ArtifactVersion]:
        identity = self.repository.get_identity(artifact_id)
        if identity is None:
            raise NotFoundError(f"artifact not found: {artifact_id}")
        current = self.repository.current_version(artifact_id)
        if current is None:
            raise NotFoundError(f"artifact has no current version: {artifact_id}")
        return identity, current

    def get_version(self, version_id: Any) -> tuple[ArtifactIdentity, ArtifactVersion]:
        version = self.repository.get_version(version_id)
        if version is None:
            raise NotFoundError(f"version not found: {version_id}")
        identity = self.repository.get_identity(version.artifact_id)
        if identity is None:
            raise NotFoundError(f"artifact not found: {version.artifact_id}")
        return identity, version

    def list_versions(self, artifact_id: Any) -> list[ArtifactVersion]:
        if self.repository.get_identity(artifact_id) is None:
            raise NotFoundError(f"artifact not found: {artifact_id}")
        return self.repository.list_versions(artifact_id)

    def list_artifacts(self, project_id: Any) -> list[tuple[ArtifactIdentity, ArtifactVersion]]:
        return self.repository.list_artifacts(project_id)

    def revise_artifact(self, command: ReviseArtifactCommand) -> ArtifactVersion:
        identity = self.repository.get_identity(command.artifact_id)
        if identity is None:
            raise NotFoundError(f"artifact not found: {command.artifact_id}")
        previous = self.repository.current_version(command.artifact_id)
        if previous is None:
            raise NotFoundError(f"artifact has no current version: {command.artifact_id}")
        try:
            version = ArtifactVersion.create(
                artifact_id=identity.id,
                project_id=identity.project_id,
                payload=command.payload,
                created_by=command.actor,
                schema_version=command.schema_version or previous.schema_version,
                revision=previous.revision + 1,
                parent_version_id=previous.id,
                provenance=command.provenance,
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return self.repository.revise_artifact(
            identity,
            previous,
            version,
            expected_current_revision=command.expected_current_revision,
        )[1]

    def transition_version(self, command: TransitionVersionCommand) -> ArtifactVersion:
        if command.expected_current_revision < 1:
            raise ValidationError("expected_current_revision must be >= 1")
        if command.target_status in {LifecycleStatus.APPROVED, LifecycleStatus.LOCKED}:
            command.actor.require_human()
        return self.repository.transition_version(
            command.version_id,
            command.target_status,
            command.actor,
            expected_current_revision=command.expected_current_revision,
            rationale=command.rationale,
        )

    def create_edge(self, command: CreateEdgeCommand) -> ArtifactEdge:
        try:
            edge = ArtifactEdge(
                    project_id=command.project_id,
                    from_version_id=command.from_version_id,
                    to_version_id=command.to_version_id,
                    edge_type=command.edge_type,
                    metadata=command.metadata,
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return self.repository.create_edge(edge)

    def lineage(self, version_id: Any, *, direction: str) -> list[ArtifactVersion]:
        return self.repository.lineage(version_id, direction=direction)

    def list_impacts(
        self, project_id: Any, *, unresolved_only: bool = False
    ) -> list[ImpactRecord]:
        return self.repository.list_impacts(project_id, unresolved_only=unresolved_only)

    def resolve_impact(self, command: ResolveImpactCommand) -> ImpactRecord:
        command.actor.require_human()
        return self.repository.resolve_impact(
            command.impact_id,
            command.classification,
            command.resolution_status,
            command.actor,
        )

    def bulk_resolve_impacts(self, command: BulkResolveImpactsCommand) -> list[ImpactRecord]:
        command.actor.require_human()
        return [
            self.repository.resolve_impact(
                impact_id,
                command.classification,
                command.resolution_status,
                command.actor,
            )
            for impact_id in command.impact_ids
        ]

    def validate_impact(
        self,
        impact_id: Any,
        *,
        contradicted: bool,
        finding: str | None,
        actor: ActorRef,
    ) -> ImpactRecord:
        actor.require_validator()
        return self.repository.validate_impact(
            impact_id, contradicted=contradicted, finding=finding, actor=actor
        )

    def create_asset(self, command: CreateAssetCommand) -> Asset:
        if self.repository.get_project(command.project_id) is None:
            raise NotFoundError(f"project not found: {command.project_id}")
        asset = Asset(
            id=uuid4(),
            project_id=command.project_id,
            asset_type=command.asset_type,
            logical_key=command.logical_key,
            lifecycle_status=LifecycleStatus.DRAFT,
            created_by=command.actor,
            created_at=datetime.now(UTC),
        )
        try:
            version = AssetVersion(
                id=uuid4(),
                asset_id=asset.id,
                project_id=command.project_id,
                revision=1,
                payload=command.payload,
                content_hash=content_hash(command.payload),
                created_by=command.actor,
                created_at=datetime.now(UTC),
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return self.repository.create_asset(asset, version)[0]

    def create_rights(self, command: CreateRightsCommand) -> RightsRecord:
        if command.record.status in {RightsStatus.DECLARED, RightsStatus.CLEARED}:
            command.actor.require_human()
        return self.repository.create_rights(command.record, command.actor)

    def approve_asset(self, command: ApproveAssetCommand) -> Asset:
        command.actor.require_human()
        return self.repository.approve_asset(command.asset_id, command.actor)

    def create_run(self, command: CreateRunCommand) -> RunRecord:
        run = RunRecord(
            id=command.run_id or uuid4(),
            project_id=command.project_id,
            model_alias=command.model_alias,
            resolved_provider=command.resolved_provider,
            resolved_model=command.resolved_model,
            provenance=command.provenance,
            disposition=command.disposition,
            created_by=command.actor,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_run(run)

    def create_provider_policy(self, command: CreateProviderPolicyCommand) -> ProviderPolicy:
        if self.repository.get_project(command.project_id) is None:
            raise NotFoundError(f"project not found: {command.project_id}")
        try:
            policy = ProviderPolicy(
                id=command.policy_id or uuid4(),
                project_id=command.project_id,
                provider=command.provider,
                model_or_service=command.model_or_service,
                captured_at=command.captured_at,
                source_url_or_document_ref=command.source_url_or_document_ref,
                commercial_use_status=command.commercial_use_status,
                retention_training_status=command.retention_training_status,
                voice_likeness_constraints=command.voice_likeness_constraints,
                distribution_constraints=command.distribution_constraints,
                allowed_for_project=command.allowed_for_project,
                block_reasons=command.block_reasons,
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return self.repository.create_provider_policy(policy)

    def list_provider_policies(self, project_id: Any) -> list[ProviderPolicy]:
        if self.repository.get_project(project_id) is None:
            raise NotFoundError(f"project not found: {project_id}")
        return self.repository.list_provider_policies(project_id)

    def create_project_event(self, command: CreateProjectEventCommand) -> ProjectEvent:
        if self.repository.get_project(command.project_id) is None:
            raise NotFoundError(f"project not found: {command.project_id}")
        event = ProjectEvent(
            id=command.event_id or uuid4(),
            project_id=command.project_id,
            event_type=command.event_type,
            subject_ref=command.subject_ref,
            payload=command.payload,
            created_by=command.actor,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_project_event(event)

    def list_project_events(self, project_id: Any) -> list[ProjectEvent]:
        if self.repository.get_project(project_id) is None:
            raise NotFoundError(f"project not found: {project_id}")
        return self.repository.list_project_events(project_id)

    def list_human_decisions(
        self, project_id: Any, *, subject_ref: str | None = None
    ) -> list[HumanDecision]:
        if self.repository.get_project(project_id) is None:
            raise NotFoundError(f"project not found: {project_id}")
        return self.repository.list_human_decisions(project_id, subject_ref=subject_ref)
