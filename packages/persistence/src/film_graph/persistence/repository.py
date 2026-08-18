"""Raw Psycopg 3 repository for M01 Postgres canon."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from film_graph.application.errors import ConflictError, NotFoundError, ValidationError
from film_graph.domain import (
    ActorRef,
    ActorType,
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
    ProjectSkillBinding,
    ProviderPolicy,
    RightsRecord,
    RightsStatus,
    RunRecord,
    to_json_compatible,
    validate_transition,
)

from .connection import connection_scope
from .errors import PersistenceUnavailable


def _jsonb(value: Any) -> Any:
    try:
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise PersistenceUnavailable(
            "psycopg[binary] is required for Postgres persistence"
        ) from exc
    return Jsonb(value)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class PostgresGraphRepository:
    """Transaction-scoped repository; no ORM or Supabase browser client."""

    def __init__(self, dsn: str | None = None, *, connection: Any | None = None) -> None:
        self.dsn = dsn or os.getenv("FPG_DATABASE_URL")
        self._connection = connection

    @contextmanager
    def _scope(self) -> Iterator[Any]:
        with connection_scope(self._connection, self.dsn) as connection:
            try:
                with connection.transaction():
                    yield connection
            except Exception:
                raise

    @staticmethod
    def _row_identity(row: Mapping[str, Any]) -> ArtifactIdentity:
        return ArtifactIdentity(
            id=UUID(str(row["id"])),
            project_id=UUID(str(row["project_id"])),
            artifact_type=str(row["artifact_type"]),
            logical_key=str(row["logical_key"]),
        )

    @staticmethod
    def _row_joined_identity(row: Mapping[str, Any]) -> ArtifactIdentity:
        return ArtifactIdentity(
            id=UUID(str(row["identity_id"])),
            project_id=UUID(str(row["identity_project_id"])),
            artifact_type=str(row["identity_artifact_type"]),
            logical_key=str(row["identity_logical_key"]),
        )

    @staticmethod
    def _row_actor(row: Mapping[str, Any], prefix: str = "created_by_") -> ActorRef:
        return ActorRef(
            ActorType(str(row[f"{prefix}actor_type"])),
            str(row[f"{prefix}actor_id"]),
        )

    @classmethod
    def _row_version(cls, row: Mapping[str, Any]) -> ArtifactVersion:
        created_at = row["created_at"]
        payload = row["payload_json"]
        provenance = row.get("provenance_json")
        return ArtifactVersion(
            id=UUID(str(row["id"])),
            artifact_id=UUID(str(row["artifact_id"])),
            project_id=UUID(str(row["project_id"])),
            schema_version=str(row["schema_version"]),
            revision=int(row["revision"]),
            lifecycle_status=LifecycleStatus(str(row["lifecycle_status"])),
            payload=payload,
            content_hash=str(row["content_hash"]),
            parent_version_id=(
                UUID(str(row["parent_version_id"])) if row.get("parent_version_id") else None
            ),
            created_by=cls._row_actor(row),
            created_at=_utc(created_at),
            provenance=provenance,
        )

    @staticmethod
    def _row_project(row: Mapping[str, Any]) -> Project:
        return Project(UUID(str(row["id"])), str(row["name"]), _utc(row["created_at"]))

    def ping(self) -> bool:
        with self._scope() as connection:
            connection.execute("select 1")
        return True

    def create_project(self, project: Project) -> Project:
        with self._scope() as connection:
            try:
                connection.execute(
                    "insert into public.projects (id, name, created_at) values (%s, %s, %s)",
                    (project.id, project.name, project.created_at),
                )
            except Exception as exc:
                raise ConflictError(f"could not create project {project.id}") from exc
        return project

    def list_projects(self) -> list[Project]:
        with self._scope() as connection:
            rows = connection.execute(
                "select id, name, created_at from public.projects order by created_at, id"
            ).fetchall()
        return [self._row_project(row) for row in rows]

    def get_project(self, project_id: UUID) -> Project | None:
        with self._scope() as connection:
            row = connection.execute(
                "select id, name, created_at from public.projects where id = %s", (project_id,)
            ).fetchone()
        return self._row_project(row) if row else None

    @staticmethod
    def _row_project_skill_binding(row: Mapping[str, Any]) -> ProjectSkillBinding:
        return ProjectSkillBinding(
            id=UUID(str(row["id"])),
            project_id=UUID(str(row["project_id"])),
            agent_ref=str(row["agent_ref"]),
            skill_name=str(row["skill_name"]),
            source_path=str(row["source_path"]),
            source_commit=str(row["source_commit"]),
            content_hash=str(row["content_hash"]),
            metadata_version=str(row["metadata_version"]),
            snapshot_hash=str(row["snapshot_hash"]),
            bound_by=ActorRef(
                ActorType(str(row["bound_by_actor_type"])),
                str(row["bound_by_actor_id"]),
            ),
            created_at=_utc(row["created_at"]),
        )

    def create_project_skill_binding(
        self, binding: ProjectSkillBinding
    ) -> ProjectSkillBinding:
        with self._scope() as connection:
            try:
                connection.execute(
                    """
                    insert into public.project_skill_locks (
                        id, project_id, agent_ref, skill_name, source_path, source_commit,
                        content_hash, metadata_version, snapshot_hash,
                        bound_by_actor_type, bound_by_actor_id, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        binding.id,
                        binding.project_id,
                        binding.agent_ref,
                        binding.skill_name,
                        binding.source_path,
                        binding.source_commit,
                        binding.content_hash,
                        binding.metadata_version,
                        binding.snapshot_hash,
                        binding.bound_by.actor_type.value,
                        binding.bound_by.actor_id,
                        binding.created_at,
                    ),
                )
            except Exception as exc:
                raise ConflictError("could not create project skill binding") from exc
        return binding

    def get_project_skill_binding(
        self, project_id: UUID, agent_ref: str, skill_name: str
    ) -> ProjectSkillBinding | None:
        with self._scope() as connection:
            row = connection.execute(
                """
                select * from public.project_skill_locks
                 where project_id = %s and agent_ref = %s and skill_name = %s
                 order by created_at desc, id desc
                 limit 1
                """,
                (project_id, agent_ref, skill_name),
            ).fetchone()
        return self._row_project_skill_binding(row) if row else None

    def list_project_skill_bindings(
        self, project_id: UUID, *, agent_ref: str | None = None
    ) -> list[ProjectSkillBinding]:
        query = "select * from public.project_skill_locks where project_id = %s"
        args: list[Any] = [project_id]
        if agent_ref is not None:
            query += " and agent_ref = %s"
            args.append(agent_ref)
        query += " order by agent_ref, skill_name, created_at, id"
        with self._scope() as connection:
            rows = connection.execute(query, args).fetchall()
        return [self._row_project_skill_binding(row) for row in rows]

    def get_identity(self, artifact_id: UUID) -> ArtifactIdentity | None:
        with self._scope() as connection:
            row = connection.execute(
                "select id, project_id, artifact_type, logical_key "
                "from public.artifact_identities where id = %s",
                (artifact_id,),
            ).fetchone()
        return self._row_identity(row) if row else None

    def get_version(self, version_id: UUID) -> ArtifactVersion | None:
        with self._scope() as connection:
            row = connection.execute(
                "select * from public.artifact_versions where id = %s", (version_id,)
            ).fetchone()
        return self._row_version(row) if row else None

    def current_version(self, artifact_id: UUID) -> ArtifactVersion | None:
        with self._scope() as connection:
            row = connection.execute(
                """
                select * from public.artifact_versions
                 where artifact_id = %s order by revision desc limit 1
                """,
                (artifact_id,),
            ).fetchone()
        return self._row_version(row) if row else None

    def list_versions(self, artifact_id: UUID) -> list[ArtifactVersion]:
        with self._scope() as connection:
            rows = connection.execute(
                "select * from public.artifact_versions where artifact_id = %s order by revision",
                (artifact_id,),
            ).fetchall()
        if not rows and self.get_identity(artifact_id) is None:
            raise NotFoundError(f"artifact not found: {artifact_id}")
        return [self._row_version(row) for row in rows]

    def create_artifact(
        self, identity: ArtifactIdentity, version: ArtifactVersion
    ) -> tuple[ArtifactIdentity, ArtifactVersion]:
        with self._scope() as connection:
            try:
                connection.execute(
                    """
                    insert into public.artifact_identities
                        (id, project_id, artifact_type, logical_key)
                    values (%s, %s, %s, %s)
                    """,
                    (
                        identity.id,
                        identity.project_id,
                        identity.artifact_type,
                        identity.logical_key,
                    ),
                )
                self._insert_version(connection, version)
            except Exception as exc:
                raise ConflictError("could not create artifact identity/version") from exc
        return identity, version

    @staticmethod
    def _insert_version(connection: Any, version: ArtifactVersion) -> None:
        connection.execute(
            """
            insert into public.artifact_versions (
                id, artifact_id, project_id, schema_version, revision, lifecycle_status,
                payload_json, content_hash, parent_version_id,
                created_by_actor_type, created_by_actor_id, created_at, provenance_json
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                version.id,
                version.artifact_id,
                version.project_id,
                version.schema_version,
                version.revision,
                version.lifecycle_status.value,
                _jsonb(to_json_compatible(version.payload)),
                version.content_hash,
                version.parent_version_id,
                version.created_by.actor_type.value,
                version.created_by.actor_id,
                version.created_at,
                _jsonb(to_json_compatible(version.provenance))
                if version.provenance is not None
                else None,
            ),
        )

    def list_artifacts(self, project_id: UUID) -> list[tuple[ArtifactIdentity, ArtifactVersion]]:
        with self._scope() as connection:
            rows = connection.execute(
                """
                select identities.id as identity_id,
                       identities.project_id as identity_project_id,
                       identities.artifact_type as identity_artifact_type,
                       identities.logical_key as identity_logical_key,
                       versions.*
                  from public.artifact_identities identities
                  join lateral (
                      select * from public.artifact_versions versions
                       where versions.artifact_id = identities.id
                       order by versions.revision desc limit 1
                  ) versions on true
                 where identities.project_id = %s
                 order by identities.logical_key, identities.id
                """,
                (project_id,),
            ).fetchall()
        return [(self._row_joined_identity(row), self._row_version(row)) for row in rows]

    def revise_artifact(
        self,
        identity: ArtifactIdentity,
        previous: ArtifactVersion,
        version: ArtifactVersion,
        *,
        expected_current_revision: int,
    ) -> tuple[ArtifactIdentity, ArtifactVersion]:
        with self._scope() as connection:
            row = connection.execute(
                """
                select * from public.artifact_versions
                 where artifact_id = %s order by revision desc limit 1 for update
                """,
                (identity.id,),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"artifact not found: {identity.id}")
            current = self._row_version(row)
            if current.revision != expected_current_revision:
                raise ConflictError(
                    "revision conflict: expected "
                    f"{expected_current_revision}, current {current.revision}"
                )
            if current.id != previous.id:
                raise ConflictError("artifact changed while revising")
            try:
                self._insert_version(connection, version)
            except Exception as exc:
                raise ConflictError("could not create artifact revision") from exc
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
        with self._scope() as connection:
            row = connection.execute(
                "select * from public.artifact_versions where id = %s for update", (version_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"version not found: {version_id}")
            version = self._row_version(row)
            current_row = connection.execute(
                """
                select * from public.artifact_versions
                 where artifact_id = %s order by revision desc limit 1 for update
                """,
                (version.artifact_id,),
            ).fetchone()
            current = self._row_version(current_row)
            if (
                current.revision != expected_current_revision
                or current.id != version_id
            ):
                raise ConflictError(
                    "lifecycle revision conflict: expected "
                    f"{expected_current_revision}, current {current.revision}"
                )
            if version.lifecycle_status is LifecycleStatus.LOCKED:
                raise ConflictError("locked versions reject all updates")
            try:
                validate_transition(version.lifecycle_status, target)
                actor.require_human() if target in {
                    LifecycleStatus.APPROVED,
                    LifecycleStatus.LOCKED,
                } else None
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc
            connection.execute(
                "update public.artifact_versions set lifecycle_status = %s where id = %s",
                (LifecycleStatus(target).value, version_id),
            )
            if target in {LifecycleStatus.APPROVED, LifecycleStatus.LOCKED}:
                connection.execute(
                    """
                    insert into public.approvals
                        (project_id, version_id, actor_type, actor_id, decision, rationale)
                    values (%s, %s, 'user', %s, %s, %s)
                    """,
                    (
                        version.project_id,
                        version.id,
                        actor.actor_id,
                        LifecycleStatus(target).value,
                        rationale,
                    ),
                )
                connection.execute(
                    """
                    insert into public.human_decisions
                        (project_id, subject_ref, decision_type, actor_type, actor_id, rationale)
                    values (%s, %s, %s, 'user', %s, %s)
                    """,
                    (
                        version.project_id,
                        str(version.id),
                        LifecycleStatus(target).value,
                        actor.actor_id,
                        rationale,
                    ),
                )
                if version.parent_version_id:
                    connection.execute(
                        """
                        with recursive descendants(version_id) as (
                            select edge.to_version_id
                              from public.artifact_edges edge
                             where edge.from_version_id = %s
                            union
                            select edge.to_version_id
                              from public.artifact_edges edge
                              join descendants path on path.version_id = edge.from_version_id
                        )
                        insert into public.impact_records (
                            project_id, cause_version_id, affected_version_id,
                            classification, reason, resolution_status
                        )
                        select %s, %s, descendants.version_id,
                               'possibly_stale', %s, 'unresolved'
                          from descendants
                         where descendants.version_id <> %s
                        on conflict (cause_version_id, affected_version_id) do nothing
                        """,
                        (
                            version.parent_version_id,
                            version.project_id,
                            version.id,
                            f"upstream version {version.parent_version_id} received a new revision",
                            version.id,
                        ),
                    )
            updated_row = connection.execute(
                "select * from public.artifact_versions where id = %s", (version_id,)
            ).fetchone()
        return self._row_version(updated_row)

    def create_edge(self, edge: ArtifactEdge) -> ArtifactEdge:
        with self._scope() as connection:
            try:
                connection.execute(
                    """
                    insert into public.artifact_edges
                        (project_id, from_version_id, to_version_id, edge_type, metadata_json)
                    values (%s, %s, %s, %s, %s)
                    on conflict (from_version_id, to_version_id, edge_type) do nothing
                    """,
                    (
                        edge.project_id,
                        edge.from_version_id,
                        edge.to_version_id,
                        edge.edge_type,
                        _jsonb(to_json_compatible(edge.metadata)),
                    ),
                )
            except Exception as exc:
                raise ConflictError("could not create artifact edge") from exc
        return edge

    def lineage(self, version_id: UUID, *, direction: str) -> list[ArtifactVersion]:
        if direction not in {"upstream", "downstream"}:
            raise ValidationError("lineage direction must be upstream or downstream")
        edge_column = "to_version_id" if direction == "upstream" else "from_version_id"
        next_column = "from_version_id" if direction == "upstream" else "to_version_id"
        with self._scope() as connection:
            rows = connection.execute(
                f"""
                with recursive lineage(version_id, depth) as (
                    select %s::uuid, 0
                    union
                    select edge.{next_column}, lineage.depth + 1
                      from public.artifact_edges edge
                      join lineage on lineage.version_id = edge.{edge_column}
                )
                select versions.*
                  from lineage
                  join public.artifact_versions versions on versions.id = lineage.version_id
                 order by lineage.depth, versions.id
                """,
                (version_id,),
            ).fetchall()
        if not rows:
            raise NotFoundError(f"version not found: {version_id}")
        return [self._row_version(row) for row in rows]

    @staticmethod
    def _row_impact(row: Mapping[str, Any]) -> ImpactRecord:
        return ImpactRecord(
            id=UUID(str(row["id"])),
            project_id=UUID(str(row["project_id"])),
            cause_version_id=UUID(str(row["cause_version_id"])),
            affected_version_id=UUID(str(row["affected_version_id"])),
            classification=ImpactClassification(str(row["classification"])),
            resolution_status=ImpactResolutionStatus(str(row["resolution_status"])),
            reason=row.get("reason"),
            validator_finding_ids=tuple(row.get("validator_finding_ids") or ()),
            created_at=_utc(row["created_at"]),
            resolved_by=(
                ActorRef(ActorType.USER, str(row["resolved_by"]))
                if row.get("resolved_by")
                else None
            ),
            resolved_at=_utc(row["resolved_at"]) if row.get("resolved_at") else None,
        )

    def list_impacts(
        self, project_id: UUID, *, unresolved_only: bool = False
    ) -> list[ImpactRecord]:
        query = "select * from public.impact_records where project_id = %s"
        args: list[Any] = [project_id]
        if unresolved_only:
            query += " and resolution_status = 'unresolved'"
        query += " order by created_at, id"
        with self._scope() as connection:
            rows = connection.execute(query, args).fetchall()
        return [self._row_impact(row) for row in rows]

    def resolve_impact(
        self,
        impact_id: UUID,
        classification: ImpactClassification,
        resolution_status: ImpactResolutionStatus,
        actor: ActorRef,
    ) -> ImpactRecord:
        actor.require_human()
        with self._scope() as connection:
            row = connection.execute(
                """
                update public.impact_records
                   set classification = %s, resolution_status = %s,
                       resolved_by = %s, resolved_at = now()
                 where id = %s
                 returning *
                """,
                (
                    ImpactClassification(classification).value,
                    ImpactResolutionStatus(resolution_status).value,
                    actor.actor_id,
                    impact_id,
                ),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"impact not found: {impact_id}")
        return self._row_impact(row)

    def validate_impact(
        self,
        impact_id: UUID,
        *,
        contradicted: bool,
        finding: str | None,
        actor: ActorRef,
    ) -> ImpactRecord:
        actor.require_validator()
        with self._scope() as connection:
            row = connection.execute(
                "select * from public.impact_records where id = %s for update", (impact_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"impact not found: {impact_id}")
            findings = list(row.get("validator_finding_ids") or ())
            if finding:
                findings.append(finding)
            updated = connection.execute(
                """
                update public.impact_records
                   set classification = %s, validator_finding_ids = %s
                 where id = %s returning *
                """,
                (
                    "contradicted" if contradicted else "possibly_stale",
                    findings,
                    impact_id,
                ),
            ).fetchone()
        return self._row_impact(updated)

    def create_asset(self, asset: Asset, version: AssetVersion) -> tuple[Asset, AssetVersion]:
        with self._scope() as connection:
            try:
                connection.execute(
                    """
                    insert into public.assets
                        (id, project_id, asset_type, logical_key, lifecycle_status,
                         created_by_actor_type, created_by_actor_id, created_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        asset.id,
                        asset.project_id,
                        asset.asset_type,
                        asset.logical_key,
                        asset.lifecycle_status.value,
                        asset.created_by.actor_type.value,
                        asset.created_by.actor_id,
                        asset.created_at,
                    ),
                )
                connection.execute(
                    """
                    insert into public.asset_versions
                        (id, asset_id, project_id, revision, payload_json, content_hash,
                         created_by_actor_type, created_by_actor_id, created_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        version.id,
                        version.asset_id,
                        version.project_id,
                        version.revision,
                        _jsonb(to_json_compatible(version.payload)),
                        version.content_hash,
                        version.created_by.actor_type.value,
                        version.created_by.actor_id,
                        version.created_at,
                    ),
                )
            except Exception as exc:
                raise ConflictError("could not create asset") from exc
        return asset, version

    def create_rights(self, record: RightsRecord, actor: ActorRef) -> RightsRecord:
        if record.status in {RightsStatus.DECLARED, RightsStatus.CLEARED}:
            actor.require_human()
        with self._scope() as connection:
            try:
                connection.execute(
                    """
                    insert into public.rights_records (
                        id, project_id, subject_ref, rights_status, source_type, holder,
                        license_or_permission, permitted_uses, territories, starts_at, expires_at,
                        attribution, evidence_asset_refs, consent_record_refs, provider_policy_ref,
                        reviewed_by, reviewed_at, attested_by_actor_type, attested_by_actor_id,
                        notes
                    ) values (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        record.id,
                        record.project_id,
                        record.subject_ref,
                        record.status.value,
                        record.source_type.value,
                        record.holder,
                        record.license_or_permission,
                        list(record.permitted_uses),
                        list(record.territories),
                        record.starts_at,
                        record.expires_at,
                        record.attribution,
                        list(record.evidence_asset_refs),
                        list(record.consent_record_refs),
                        record.provider_policy_ref,
                        record.reviewed_by,
                        record.reviewed_at,
                        actor.actor_type.value,
                        actor.actor_id,
                        list(record.notes),
                    ),
                )
            except Exception as exc:
                raise ConflictError("could not create rights record") from exc
        return record

    def approve_asset(self, asset_id: UUID, actor: ActorRef) -> Asset:
        actor.require_human()
        with self._scope() as connection:
            row = connection.execute(
                "select * from public.assets where id = %s for update", (asset_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"asset not found: {asset_id}")
            try:
                updated = connection.execute(
                    """
                    update public.assets set lifecycle_status = 'approved'
                     where id = %s returning *
                    """,
                    (asset_id,),
                ).fetchone()
            except Exception as exc:
                raise ConflictError("asset approval requires declared or cleared rights") from exc
            connection.execute(
                """
                insert into public.human_decisions
                    (project_id, subject_ref, decision_type, actor_type, actor_id, rationale)
                values (%s, %s, 'asset_approved', 'user', %s, null)
                """,
                (UUID(str(updated["project_id"])), str(asset_id), actor.actor_id),
            )
        return Asset(
            id=UUID(str(updated["id"])),
            project_id=UUID(str(updated["project_id"])),
            asset_type=str(updated["asset_type"]),
            logical_key=str(updated["logical_key"]),
            lifecycle_status=LifecycleStatus(str(updated["lifecycle_status"])),
            created_by=ActorRef(
                ActorType(str(updated["created_by_actor_type"])),
                str(updated["created_by_actor_id"]),
            ),
            created_at=_utc(updated["created_at"]),
        )

    def create_run(self, run: RunRecord) -> RunRecord:
        with self._scope() as connection:
            connection.execute(
                """
                insert into public.run_records (
                    id, project_id, model_alias, resolved_provider, resolved_model,
                    provenance_json, disposition, created_by_actor_type,
                    created_by_actor_id, created_at
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run.id,
                    run.project_id,
                    run.model_alias,
                    run.resolved_provider,
                    run.resolved_model,
                    _jsonb(to_json_compatible(run.provenance)),
                    run.disposition,
                    run.created_by.actor_type.value,
                    run.created_by.actor_id,
                    run.created_at,
                ),
            )
        return run

    @staticmethod
    def _row_provider_policy(row: Mapping[str, Any]) -> ProviderPolicy:
        return ProviderPolicy(
            id=UUID(str(row["id"])),
            project_id=UUID(str(row["project_id"])),
            provider=str(row["provider"]),
            model_or_service=row.get("model_or_service"),
            captured_at=_utc(row["captured_at"]),
            source_url_or_document_ref=row.get("source_url_or_document_ref"),
            commercial_use_status=str(row["commercial_use_status"]),
            retention_training_status=str(row["retention_training_status"]),
            voice_likeness_constraints=tuple(row.get("voice_likeness_constraints") or ()),
            distribution_constraints=tuple(row.get("distribution_constraints") or ()),
            allowed_for_project=bool(row["allowed_for_project"]),
            block_reasons=tuple(row.get("block_reasons") or ()),
        )

    def create_provider_policy(self, policy: ProviderPolicy) -> ProviderPolicy:
        with self._scope() as connection:
            try:
                connection.execute(
                    """
                    insert into public.provider_policies (
                        id, project_id, provider, model_or_service, captured_at,
                        source_url_or_document_ref, commercial_use_status,
                        retention_training_status, voice_likeness_constraints,
                        distribution_constraints, allowed_for_project, block_reasons
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        policy.id,
                        policy.project_id,
                        policy.provider,
                        policy.model_or_service,
                        policy.captured_at,
                        policy.source_url_or_document_ref,
                        policy.commercial_use_status,
                        policy.retention_training_status,
                        list(policy.voice_likeness_constraints),
                        list(policy.distribution_constraints),
                        policy.allowed_for_project,
                        list(policy.block_reasons),
                    ),
                )
            except Exception as exc:
                raise ConflictError("could not create provider policy snapshot") from exc
        return policy

    def list_provider_policies(self, project_id: UUID) -> list[ProviderPolicy]:
        with self._scope() as connection:
            rows = connection.execute(
                "select * from public.provider_policies where project_id = %s "
                "order by captured_at, id",
                (project_id,),
            ).fetchall()
        return [self._row_provider_policy(row) for row in rows]

    @staticmethod
    def _row_human_decision(row: Mapping[str, Any]) -> HumanDecision:
        return HumanDecision(
            id=UUID(str(row["id"])),
            project_id=UUID(str(row["project_id"])),
            subject_ref=str(row["subject_ref"]),
            decision_type=str(row["decision_type"]),
            actor=ActorRef(ActorType.USER, str(row["actor_id"])),
            rationale=row.get("rationale"),
            created_at=_utc(row["created_at"]),
        )

    def list_human_decisions(
        self, project_id: UUID, *, subject_ref: str | None = None
    ) -> list[HumanDecision]:
        query = "select * from public.human_decisions where project_id = %s"
        args: list[Any] = [project_id]
        if subject_ref is not None:
            query += " and subject_ref = %s"
            args.append(subject_ref)
        query += " order by created_at, id"
        with self._scope() as connection:
            rows = connection.execute(query, args).fetchall()
        return [self._row_human_decision(row) for row in rows]

    @staticmethod
    def _row_project_event(row: Mapping[str, Any]) -> ProjectEvent:
        return ProjectEvent(
            id=UUID(str(row["id"])),
            project_id=UUID(str(row["project_id"])),
            event_type=str(row["event_type"]),
            subject_ref=row.get("subject_ref"),
            payload=row.get("payload_json") or {},
            created_by=ActorRef(
                ActorType(str(row["created_by_actor_type"])),
                str(row["created_by_actor_id"]),
            ),
            created_at=_utc(row["created_at"]),
        )

    def create_project_event(self, event: ProjectEvent) -> ProjectEvent:
        with self._scope() as connection:
            try:
                connection.execute(
                    """
                    insert into public.project_events (
                        id, project_id, event_type, subject_ref, payload_json,
                        created_by_actor_type, created_by_actor_id, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event.id,
                        event.project_id,
                        event.event_type,
                        event.subject_ref,
                        _jsonb(to_json_compatible(event.payload)),
                        event.created_by.actor_type.value,
                        event.created_by.actor_id,
                        event.created_at,
                    ),
                )
            except Exception as exc:
                raise ConflictError("could not create project event") from exc
        return event

    def list_project_events(self, project_id: UUID) -> list[ProjectEvent]:
        with self._scope() as connection:
            rows = connection.execute(
                "select * from public.project_events where project_id = %s "
                "order by created_at, id",
                (project_id,),
            ).fetchall()
        return [self._row_project_event(row) for row in rows]
