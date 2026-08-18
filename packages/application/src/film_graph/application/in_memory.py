"""Deterministic repository adapter for application/API tests.

This adapter is not production persistence.  It mirrors the M01 repository
port closely enough to exercise authority, concurrency, graph, impact, and
rights behavior without network or database credentials.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from film_graph.domain import (
    ActorRef,
    ArtifactEdge,
    ArtifactIdentity,
    ArtifactVersion,
    Asset,
    AssetVersion,
    HumanDecision,
    ImpactClassification,
    ImpactRecord,
    ImpactResolutionStatus,
    LifecycleStatus,
    Project,
    ProjectEvent,
    ProviderPolicy,
    RightsRecord,
    RightsStatus,
    RunRecord,
    validate_transition,
)

from .errors import ConflictError, NotFoundError, ValidationError


class InMemoryGraphRepository:
    """A small, process-local repository used by deterministic tests."""

    def __init__(self) -> None:
        self.projects: dict[UUID, Project] = {}
        self.identities: dict[UUID, ArtifactIdentity] = {}
        self.versions: dict[UUID, ArtifactVersion] = {}
        self.current_by_artifact: dict[UUID, UUID] = {}
        self.edges: dict[tuple[UUID, UUID, str], ArtifactEdge] = {}
        self.impacts: dict[tuple[UUID, UUID], ImpactRecord] = {}
        self.assets: dict[UUID, Asset] = {}
        self.asset_versions: dict[UUID, AssetVersion] = {}
        self.rights: dict[UUID, RightsRecord] = {}
        self.rights_attesters: dict[UUID, ActorRef] = {}
        self.runs: dict[UUID, RunRecord] = {}
        self.provider_policies: dict[UUID, ProviderPolicy] = {}
        self.human_decisions: list[HumanDecision] = []
        self.approvals: list[dict[str, object]] = []
        self.project_events: dict[UUID, ProjectEvent] = {}

    def create_project(self, project: Project) -> Project:
        if project.id in self.projects:
            raise ConflictError(f"project already exists: {project.id}")
        self.projects[project.id] = project
        return project

    def list_projects(self) -> list[Project]:
        return sorted(self.projects.values(), key=lambda item: item.created_at)

    def get_project(self, project_id: UUID) -> Project | None:
        return self.projects.get(project_id)

    def _require_project(self, project_id: UUID) -> Project:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFoundError(f"project not found: {project_id}")
        return project

    def create_artifact(
        self, identity: ArtifactIdentity, version: ArtifactVersion
    ) -> tuple[ArtifactIdentity, ArtifactVersion]:
        self._require_project(identity.project_id)
        if identity.id in self.identities:
            raise ConflictError(f"artifact already exists: {identity.id}")
        if any(
            value.project_id == identity.project_id
            and value.artifact_type == identity.artifact_type
            and value.logical_key == identity.logical_key
            for value in self.identities.values()
        ):
            raise ConflictError("artifact logical_key already exists in project")
        if version.project_id != identity.project_id or version.artifact_id != identity.id:
            raise ValidationError("artifact identity/version project or identity mismatch")
        self.identities[identity.id] = identity
        self.versions[version.id] = version
        self.current_by_artifact[identity.id] = version.id
        return identity, version

    def get_identity(self, artifact_id: UUID) -> ArtifactIdentity | None:
        return self.identities.get(artifact_id)

    def get_version(self, version_id: UUID) -> ArtifactVersion | None:
        return self.versions.get(version_id)

    def current_version(self, artifact_id: UUID) -> ArtifactVersion | None:
        version_id = self.current_by_artifact.get(artifact_id)
        return self.versions.get(version_id) if version_id else None

    def list_versions(self, artifact_id: UUID) -> list[ArtifactVersion]:
        if artifact_id not in self.identities:
            raise NotFoundError(f"artifact not found: {artifact_id}")
        return sorted(
            (item for item in self.versions.values() if item.artifact_id == artifact_id),
            key=lambda item: item.revision,
        )

    def list_artifacts(self, project_id: UUID) -> list[tuple[ArtifactIdentity, ArtifactVersion]]:
        self._require_project(project_id)
        result: list[tuple[ArtifactIdentity, ArtifactVersion]] = []
        for identity in self.identities.values():
            if identity.project_id != project_id:
                continue
            current = self.current_version(identity.id)
            if current is not None:
                result.append((identity, current))
        return sorted(result, key=lambda item: item[0].logical_key)

    def revise_artifact(
        self,
        identity: ArtifactIdentity,
        previous: ArtifactVersion,
        version: ArtifactVersion,
        *,
        expected_current_revision: int,
    ) -> tuple[ArtifactIdentity, ArtifactVersion]:
        current = self.current_version(identity.id)
        if current is None:
            raise NotFoundError(f"artifact not found: {identity.id}")
        if current.revision != expected_current_revision:
            raise ConflictError(
                "revision conflict: expected "
                f"{expected_current_revision}, current {current.revision}"
            )
        if previous.id != current.id:
            raise ConflictError("artifact changed while revising")
        if version.parent_version_id != previous.id or version.revision != previous.revision + 1:
            raise ValidationError("revision must link the current version and increment revision")
        if version.id in self.versions:
            raise ConflictError(f"version already exists: {version.id}")
        self.versions[version.id] = version
        self.current_by_artifact[identity.id] = version.id
        return identity, version

    def transition_version(
        self,
        version_id: UUID,
        target: LifecycleStatus,
        actor: ActorRef,
        *,
        expected_current_revision: int,
        rationale: str | None,
    ) -> ArtifactVersion:
        current = self.versions.get(version_id)
        if current is None:
            raise NotFoundError(f"version not found: {version_id}")
        current_version = self.current_version(current.artifact_id)
        if current_version is None:
            raise NotFoundError(f"artifact not found: {current.artifact_id}")
        if (
            current_version.revision != expected_current_revision
            or current_version.id != version_id
        ):
            raise ConflictError(
                "lifecycle revision conflict: expected "
                f"{expected_current_revision}, current {current_version.revision}"
            )
        if current.lifecycle_status is LifecycleStatus.LOCKED:
            raise ConflictError("locked versions reject all updates")
        try:
            validate_transition(current.lifecycle_status, target)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        updated = replace(current, lifecycle_status=LifecycleStatus(target))
        self.versions[version_id] = updated
        if updated.lifecycle_status in {LifecycleStatus.APPROVED, LifecycleStatus.LOCKED}:
            self._create_impacts_for_revision(updated)
            self.approvals.append(
                {
                    "version_id": updated.id,
                    "actor": actor,
                    "decision": updated.lifecycle_status.value,
                    "rationale": rationale,
                }
            )
            self.human_decisions.append(
                HumanDecision(
                    id=uuid4(),
                    project_id=updated.project_id,
                    subject_ref=str(updated.id),
                    decision_type=updated.lifecycle_status.value,
                    actor=actor,
                    rationale=rationale,
                    created_at=datetime.now(UTC),
                )
            )
        return updated

    def create_edge(self, edge: ArtifactEdge) -> ArtifactEdge:
        self._require_project(edge.project_id)
        from_version = self.versions.get(edge.from_version_id)
        to_version = self.versions.get(edge.to_version_id)
        if from_version is None or to_version is None:
            raise NotFoundError("edge endpoint version not found")
        if from_version.project_id != edge.project_id or to_version.project_id != edge.project_id:
            raise ConflictError("cross-project artifact edge is not allowed")
        key = (edge.from_version_id, edge.to_version_id, edge.edge_type)
        if key in self.edges:
            return self.edges[key]
        if self._reachable(edge.to_version_id, edge.from_version_id):
            raise ConflictError("artifact dependency cycle detected")
        self.edges[key] = edge
        return edge

    def _neighbors(self, version_id: UUID, *, direction: str) -> list[UUID]:
        if direction == "downstream":
            return [
                edge.to_version_id
                for edge in self.edges.values()
                if edge.from_version_id == version_id
            ]
        return [
            edge.from_version_id for edge in self.edges.values() if edge.to_version_id == version_id
        ]

    def _reachable(self, start: UUID, target: UUID) -> bool:
        seen: set[UUID] = set()
        queue = [start]
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            if current == target:
                return True
            queue.extend(self._neighbors(current, direction="downstream"))
        return False

    def lineage(self, version_id: UUID, *, direction: str) -> list[ArtifactVersion]:
        if version_id not in self.versions:
            raise NotFoundError(f"version not found: {version_id}")
        if direction not in {"upstream", "downstream"}:
            raise ValidationError("lineage direction must be upstream or downstream")
        result: list[ArtifactVersion] = []
        seen: set[UUID] = set()
        queue = [version_id]
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            result.append(self.versions[current])
            queue.extend(self._neighbors(current, direction=direction))
        return result

    def _create_impacts_for_revision(self, cause: ArtifactVersion) -> None:
        if cause.parent_version_id is None:
            return
        for affected_id in self._descendants(cause.parent_version_id):
            if affected_id == cause.id:
                continue
            key = (cause.id, affected_id)
            if key in self.impacts:
                continue
            self.impacts[key] = ImpactRecord.create(
                project_id=cause.project_id,
                cause_version_id=cause.id,
                affected_version_id=affected_id,
                reason=f"upstream version {cause.parent_version_id} received a new revision",
            )

    def _descendants(self, start: UUID) -> list[UUID]:
        result: list[UUID] = []
        queue = self._neighbors(start, direction="downstream")
        seen: set[UUID] = set()
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            result.append(current)
            queue.extend(self._neighbors(current, direction="downstream"))
        return result

    def list_impacts(
        self, project_id: UUID, *, unresolved_only: bool = False
    ) -> list[ImpactRecord]:
        self._require_project(project_id)
        records = [item for item in self.impacts.values() if item.project_id == project_id]
        if unresolved_only:
            records = [
                item
                for item in records
                if item.resolution_status is ImpactResolutionStatus.UNRESOLVED
            ]
        return sorted(records, key=lambda item: item.created_at)

    def resolve_impact(
        self,
        impact_id: UUID,
        classification: ImpactClassification,
        resolution_status: ImpactResolutionStatus,
        actor: ActorRef,
    ) -> ImpactRecord:
        record = next((item for item in self.impacts.values() if item.id == impact_id), None)
        if record is None:
            raise NotFoundError(f"impact not found: {impact_id}")
        updated = replace(
            record,
            classification=ImpactClassification(classification),
            resolution_status=ImpactResolutionStatus(resolution_status),
            resolved_by=actor,
            resolved_at=datetime.now(UTC),
        )
        self.impacts[(record.cause_version_id, record.affected_version_id)] = updated
        return updated

    def validate_impact(
        self,
        impact_id: UUID,
        *,
        contradicted: bool,
        finding: str | None,
        actor: ActorRef,
    ) -> ImpactRecord:
        actor.require_validator()
        record = next((item for item in self.impacts.values() if item.id == impact_id), None)
        if record is None:
            raise NotFoundError(f"impact not found: {impact_id}")
        classification = (
            ImpactClassification.CONTRADICTED
            if contradicted
            else ImpactClassification.POSSIBLY_STALE
        )
        findings = record.validator_finding_ids + ((finding,) if finding else ())
        updated = replace(record, classification=classification, validator_finding_ids=findings)
        self.impacts[(record.cause_version_id, record.affected_version_id)] = updated
        return updated

    def create_asset(self, asset: Asset, version: AssetVersion) -> tuple[Asset, AssetVersion]:
        self._require_project(asset.project_id)
        if asset.id in self.assets:
            raise ConflictError(f"asset already exists: {asset.id}")
        if version.asset_id != asset.id or version.project_id != asset.project_id:
            raise ValidationError("asset version must belong to the asset project")
        self.assets[asset.id] = asset
        self.asset_versions[version.id] = version
        return asset, version

    def create_rights(self, record: RightsRecord, actor: ActorRef) -> RightsRecord:
        self._require_project(record.project_id)
        if record.status in {RightsStatus.DECLARED, RightsStatus.CLEARED}:
            actor.require_human()
        if record.id in self.rights:
            raise ConflictError(f"rights record already exists: {record.id}")
        self.rights[record.id] = record
        self.rights_attesters[record.id] = actor
        return record

    def approve_asset(self, asset_id: UUID, actor: ActorRef) -> Asset:
        asset = self.assets.get(asset_id)
        if asset is None:
            raise NotFoundError(f"asset not found: {asset_id}")
        if not any(
            record.project_id == asset.project_id
            and record.subject_ref == str(asset.id)
            and record.permits_approval
            for record in self.rights.values()
        ):
            raise ConflictError("asset approval requires declared or cleared rights")
        if asset.lifecycle_status is LifecycleStatus.LOCKED:
            raise ConflictError("locked assets reject all updates")
        updated = replace(asset, lifecycle_status=LifecycleStatus.APPROVED)
        self.assets[asset_id] = updated
        self.human_decisions.append(
            HumanDecision(
                id=uuid4(),
                project_id=asset.project_id,
                subject_ref=str(asset.id),
                decision_type="asset_approved",
                actor=actor,
                rationale=None,
                created_at=datetime.now(UTC),
            )
        )
        return updated

    def create_run(self, run: RunRecord) -> RunRecord:
        self._require_project(run.project_id)
        if run.id in self.runs:
            raise ConflictError(f"run already exists: {run.id}")
        self.runs[run.id] = run
        return run

    def create_provider_policy(self, policy: ProviderPolicy) -> ProviderPolicy:
        self._require_project(policy.project_id)
        if policy.id in self.provider_policies:
            raise ConflictError(f"provider policy already exists: {policy.id}")
        self.provider_policies[policy.id] = policy
        return policy

    def list_provider_policies(self, project_id: UUID) -> list[ProviderPolicy]:
        self._require_project(project_id)
        return sorted(
            (item for item in self.provider_policies.values() if item.project_id == project_id),
            key=lambda item: item.captured_at,
        )

    def create_project_event(self, event: ProjectEvent) -> ProjectEvent:
        self._require_project(event.project_id)
        if event.id in self.project_events:
            raise ConflictError(f"project event already exists: {event.id}")
        self.project_events[event.id] = event
        return event

    def list_project_events(self, project_id: UUID) -> list[ProjectEvent]:
        self._require_project(project_id)
        return sorted(
            (item for item in self.project_events.values() if item.project_id == project_id),
            key=lambda item: item.created_at,
        )

    def list_human_decisions(
        self, project_id: UUID, *, subject_ref: str | None = None
    ) -> list[HumanDecision]:
        self._require_project(project_id)
        return [
            item
            for item in self.human_decisions
            if item.project_id == project_id
            and (subject_ref is None or item.subject_ref == subject_ref)
        ]
