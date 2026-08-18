-- M01 Artifact, Lineage, Impact, and Rights Core.
-- Postgres is canonical; adapters must never update a locked payload in place.

create extension if not exists pgcrypto;

create table if not exists public.projects (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(btrim(name)) > 0),
    created_at timestamptz not null default now()
);

create table if not exists public.artifact_identities (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    artifact_type text not null check (artifact_type = any (array[
        'creative_constitution', 'evidence_item', 'premise_candidate', 'character',
        'relationship', 'beat', 'sequence', 'scene_contract', 'screenplay_scene',
        'screenplay_patch', 'critic_finding', 'delivery_spec', 'budget_plan'
    ])),
    logical_key text not null check (length(btrim(logical_key)) > 0),
    unique (project_id, artifact_type, logical_key),
    unique (id, project_id)
);

create table if not exists public.artifact_versions (
    id uuid primary key default gen_random_uuid(),
    artifact_id uuid not null,
    project_id uuid not null,
    schema_version text not null check (schema_version ~ '^[0-9]+\.[0-9]+(?:\.[0-9]+)?$'),
    revision integer not null check (revision >= 1),
    lifecycle_status text not null check (lifecycle_status = any (array[
        'draft', 'validated', 'human_review', 'approved', 'locked', 'rejected', 'deprecated'
    ])),
    payload_json jsonb not null check (jsonb_typeof(payload_json) = 'object'),
    content_hash text not null check (content_hash ~ '^[a-f0-9]{64}$'),
    parent_version_id uuid references public.artifact_versions(id),
    created_by_actor_type text not null check (created_by_actor_type = any (array[
        'user', 'agent', 'workflow', 'system', 'import'
    ])),
    created_by_actor_id text not null check (length(btrim(created_by_actor_id)) > 0),
    created_at timestamptz not null default now(),
    provenance_json jsonb,
    unique (artifact_id, revision),
    unique (id, project_id),
    foreign key (artifact_id, project_id)
        references public.artifact_identities(id, project_id)
        on delete cascade
);

create index if not exists artifact_versions_current_idx
    on public.artifact_versions (artifact_id, revision desc);

create or replace function public.fpg_check_artifact_version_scope()
returns trigger
language plpgsql
as $$
declare
    parent_project uuid;
    parent_artifact uuid;
begin
    if new.parent_version_id is not null then
        select project_id, artifact_id
          into parent_project, parent_artifact
          from public.artifact_versions
         where id = new.parent_version_id;
        if parent_project is null then
            raise exception 'parent artifact version does not exist' using errcode = '23503';
        end if;
        if parent_project <> new.project_id or parent_artifact <> new.artifact_id then
            raise exception 'parent version must belong to the same project and artifact'
                using errcode = '23514';
        end if;
    end if;
    return new;
end;
$$;

drop trigger if exists artifact_versions_scope_trg on public.artifact_versions;
create trigger artifact_versions_scope_trg
before insert on public.artifact_versions
for each row execute function public.fpg_check_artifact_version_scope();

create or replace function public.fpg_reject_locked_or_payload_mutation()
returns trigger
language plpgsql
as $$
begin
    if old.lifecycle_status = 'locked' then
        raise exception 'locked artifact versions reject all updates' using errcode = '55000';
    end if;
    if not (
        (old.lifecycle_status = 'draft' and new.lifecycle_status = 'validated')
        or (old.lifecycle_status = 'validated' and new.lifecycle_status = 'human_review')
        or (old.lifecycle_status = 'human_review' and new.lifecycle_status in ('approved', 'rejected'))
        or (old.lifecycle_status = 'approved' and new.lifecycle_status = 'locked')
    ) then
        raise exception 'invalid artifact lifecycle transition from % to %',
            old.lifecycle_status, new.lifecycle_status using errcode = '23514';
    end if;
    if old.payload_json is distinct from new.payload_json
       or old.content_hash is distinct from new.content_hash
       or old.artifact_id is distinct from new.artifact_id
       or old.project_id is distinct from new.project_id
       or old.schema_version is distinct from new.schema_version
       or old.revision is distinct from new.revision
       or old.parent_version_id is distinct from new.parent_version_id
       or old.created_by_actor_type is distinct from new.created_by_actor_type
       or old.created_by_actor_id is distinct from new.created_by_actor_id
       or old.created_at is distinct from new.created_at
       or old.provenance_json is distinct from new.provenance_json then
        raise exception 'artifact payload/version provenance is immutable; create a revision'
            using errcode = '55000';
    end if;
    return new;
end;
$$;

drop trigger if exists artifact_versions_immutable_trg on public.artifact_versions;
create trigger artifact_versions_immutable_trg
before update on public.artifact_versions
for each row execute function public.fpg_reject_locked_or_payload_mutation();

create table if not exists public.artifact_edges (
    project_id uuid not null references public.projects(id) on delete cascade,
    from_version_id uuid not null,
    to_version_id uuid not null,
    edge_type text not null check (edge_type = any (array[
        'DERIVED_FROM', 'REQUIRES', 'IMPLEMENTS', 'USES_ASSET', 'PAYS_OFF',
        'CONTRADICTS', 'SUPERSEDES', 'SELECTED_FROM'
    ])),
    metadata_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    primary key (from_version_id, to_version_id, edge_type),
    check (from_version_id <> to_version_id),
    foreign key (from_version_id, project_id)
        references public.artifact_versions(id, project_id)
        on delete cascade,
    foreign key (to_version_id, project_id)
        references public.artifact_versions(id, project_id)
        on delete cascade
);

create or replace function public.fpg_check_edge_cycle_and_scope()
returns trigger
language plpgsql
as $$
begin
    if exists (
        with recursive reachable(version_id) as (
            select new.to_version_id
            union
            select edge.to_version_id
              from public.artifact_edges edge
              join reachable path on path.version_id = edge.from_version_id
        )
        select 1 from reachable where version_id = new.from_version_id
    ) then
        raise exception 'artifact dependency cycle detected' using errcode = '23514';
    end if;
    return new;
end;
$$;

drop trigger if exists artifact_edges_cycle_trg on public.artifact_edges;
create trigger artifact_edges_cycle_trg
before insert on public.artifact_edges
for each row execute function public.fpg_check_edge_cycle_and_scope();

create index if not exists artifact_edges_from_idx on public.artifact_edges (from_version_id);
create index if not exists artifact_edges_to_idx on public.artifact_edges (to_version_id);

create table if not exists public.impact_records (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    cause_version_id uuid not null,
    affected_version_id uuid not null,
    classification text not null check (classification = any (array[
        'possibly_stale', 'contradicted', 'reviewed_valid', 'rederive_requested', 'resolved'
    ])),
    reason text,
    validator_finding_ids text[] not null default '{}',
    resolution_status text not null check (resolution_status = any (array[
        'unresolved', 'acknowledged', 'revalidate_requested', 'rederive_requested', 'resolved'
    ])),
    resolved_by text,
    resolved_at timestamptz,
    created_at timestamptz not null default now(),
    unique (cause_version_id, affected_version_id),
    check (cause_version_id <> affected_version_id),
    foreign key (cause_version_id, project_id)
        references public.artifact_versions(id, project_id) on delete cascade,
    foreign key (affected_version_id, project_id)
        references public.artifact_versions(id, project_id) on delete cascade
);

create index if not exists impact_records_project_idx
    on public.impact_records (project_id, resolution_status, created_at);

create table if not exists public.approvals (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    version_id uuid not null,
    actor_type text not null check (actor_type = 'user'),
    actor_id text not null check (length(btrim(actor_id)) > 0),
    decision text not null check (decision = any (array['approved', 'rejected', 'locked'])),
    rationale text,
    created_at timestamptz not null default now(),
    foreign key (version_id, project_id)
        references public.artifact_versions(id, project_id) on delete cascade
);

create table if not exists public.human_decisions (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    subject_ref text not null,
    decision_type text not null,
    actor_type text not null default 'user' check (actor_type = 'user'),
    actor_id text not null check (length(btrim(actor_id)) > 0),
    rationale text,
    created_at timestamptz not null default now()
);

create table if not exists public.assets (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    asset_type text not null check (length(btrim(asset_type)) > 0),
    logical_key text not null check (length(btrim(logical_key)) > 0),
    lifecycle_status text not null default 'draft' check (lifecycle_status = any (array[
        'draft', 'validated', 'human_review', 'approved', 'locked', 'rejected', 'deprecated'
    ])),
    created_by_actor_type text not null check (created_by_actor_type = any (array[
        'user', 'agent', 'workflow', 'system', 'import'
    ])),
    created_by_actor_id text not null check (length(btrim(created_by_actor_id)) > 0),
    created_at timestamptz not null default now(),
    unique (project_id, asset_type, logical_key),
    unique (id, project_id)
);

create table if not exists public.asset_versions (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets(id) on delete cascade,
    project_id uuid not null references public.projects(id) on delete cascade,
    revision integer not null check (revision >= 1),
    payload_json jsonb not null check (jsonb_typeof(payload_json) = 'object'),
    content_hash text not null check (content_hash ~ '^[a-f0-9]{64}$'),
    created_by_actor_type text not null check (created_by_actor_type = any (array[
        'user', 'agent', 'workflow', 'system', 'import'
    ])),
    created_by_actor_id text not null check (length(btrim(created_by_actor_id)) > 0),
    created_at timestamptz not null default now(),
    unique (asset_id, revision),
    unique (id, project_id),
    foreign key (asset_id, project_id)
        references public.assets(id, project_id) on delete cascade
);

create or replace function public.fpg_reject_asset_version_mutation()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' and not exists (
        select 1 from public.assets where id = old.asset_id
    ) then
        -- The parent asset/project has already been removed; permit the
        -- declared ON DELETE CASCADE cleanup path.
        return old;
    end if;
    raise exception 'asset versions are append-only; create a new version'
        using errcode = '55000';
end;
$$;

drop trigger if exists asset_versions_immutable_trg on public.asset_versions;
create trigger asset_versions_immutable_trg
before update or delete on public.asset_versions
for each row execute function public.fpg_reject_asset_version_mutation();

create table if not exists public.rights_records (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    subject_ref text not null,
    rights_status text not null check (rights_status = any (array[
        'unverified', 'declared', 'cleared', 'restricted', 'expired', 'rejected'
    ])),
    source_type text not null check (source_type = any (array[
        'self_created', 'licensed', 'public_domain', 'provider_generated',
        'commissioned', 'consented_voice', 'consented_likeness', 'unknown'
    ])),
    holder text not null check (length(btrim(holder)) > 0),
    license_or_permission text,
    permitted_uses text[] not null check (
        cardinality(permitted_uses) > 0
        and permitted_uses <@ array[
            'internal_development', 'festival', 'streaming',
            'commercial_distribution', 'advertising', 'film_tv',
            'games', 'social_media', 'training'
        ]::text[]
    ),
    territories text[] not null check (cardinality(territories) > 0),
    starts_at timestamptz,
    expires_at timestamptz,
    attribution text,
    evidence_asset_refs text[] not null default '{}',
    consent_record_refs text[] not null default '{}',
    provider_policy_ref text,
    reviewed_by text,
    reviewed_at timestamptz,
    attested_by_actor_type text not null check (attested_by_actor_type = any (array[
        'user', 'agent', 'workflow', 'system', 'import'
    ])),
    attested_by_actor_id text not null check (length(btrim(attested_by_actor_id)) > 0),
    notes text[] not null default '{}',
    created_at timestamptz not null default now(),
    check (expires_at is null or starts_at is null or expires_at > starts_at),
    check (rights_status not in ('declared', 'cleared') or (
        reviewed_by is not null
        and reviewed_at is not null
        and attested_by_actor_type = 'user'
    ))
);

create index if not exists rights_records_subject_idx
    on public.rights_records (project_id, subject_ref, rights_status);

create or replace function public.fpg_require_asset_rights_for_approval()
returns trigger
language plpgsql
as $$
begin
    if new.lifecycle_status = 'approved'
       and (tg_op = 'INSERT' or old.lifecycle_status <> 'approved') then
        if not exists (
            select 1
              from public.rights_records rights
             where rights.project_id = new.project_id
               and rights.subject_ref = new.id::text
               and rights.rights_status in ('declared', 'cleared')
        ) then
            raise exception 'asset approval requires a declared or cleared rights record'
                using errcode = '23514';
        end if;
    end if;
    return new;
end;
$$;

drop trigger if exists assets_rights_gate_trg on public.assets;
create trigger assets_rights_gate_trg
before insert or update on public.assets
for each row execute function public.fpg_require_asset_rights_for_approval();

create table if not exists public.provider_policies (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    provider text not null,
    model_or_service text,
    captured_at timestamptz not null,
    source_url_or_document_ref text,
    commercial_use_status text not null check (commercial_use_status = any (array[
        'allowed', 'restricted', 'unknown', 'disallowed'
    ])),
    retention_training_status text not null check (retention_training_status = any (array[
        'no_training', 'opt_out_configured', 'may_train', 'unknown'
    ])),
    voice_likeness_constraints text[] not null default '{}',
    distribution_constraints text[] not null default '{}',
    allowed_for_project boolean not null,
    block_reasons text[] not null default '{}'
);

create table if not exists public.run_records (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    model_alias text,
    resolved_provider text,
    resolved_model text,
    provenance_json jsonb not null default '{}'::jsonb,
    disposition text not null,
    created_by_actor_type text not null check (created_by_actor_type = any (array[
        'user', 'agent', 'workflow', 'system', 'import'
    ])),
    created_by_actor_id text not null check (length(btrim(created_by_actor_id)) > 0),
    created_at timestamptz not null default now()
);

create table if not exists public.project_events (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    event_type text not null,
    subject_ref text,
    payload_json jsonb not null default '{}'::jsonb,
    created_by_actor_type text not null check (created_by_actor_type = any (array[
        'user', 'agent', 'workflow', 'system', 'import'
    ])),
    created_by_actor_id text not null check (length(btrim(created_by_actor_id)) > 0),
    created_at timestamptz not null default now()
);
