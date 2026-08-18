-- M02 exact project-to-skill bindings.
-- A binding records a resolved reference, not a floating skill name.

create table if not exists public.project_skill_locks (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    agent_ref text not null check (length(btrim(agent_ref)) > 0),
    skill_name text not null check (skill_name ~ '^[a-z][a-z0-9-]{1,63}$'),
    source_path text not null check (
        length(btrim(source_path)) > 0
        and source_path !~ '^/'
        and source_path !~ '(^|/)\.\.?(/|$)'
        and source_path !~ '\\'
    ),
    source_commit text not null check (source_commit ~ '^[0-9a-f]{7,40}$'),
    content_hash text not null check (content_hash ~ '^sha256:[a-f0-9]{64}$'),
    metadata_version text not null check (length(btrim(metadata_version)) > 0),
    snapshot_hash text not null check (snapshot_hash ~ '^sha256:[a-f0-9]{64}$'),
    bound_by_actor_type text not null check (bound_by_actor_type = 'user'),
    bound_by_actor_id text not null check (length(btrim(bound_by_actor_id)) > 0),
    created_at timestamptz not null default now(),
    constraint project_skill_locks_exact_snapshot_key
        unique (project_id, agent_ref, skill_name, snapshot_hash)
);

create index if not exists project_skill_locks_project_agent_idx
    on public.project_skill_locks (project_id, agent_ref, skill_name, created_at desc, id desc);

create or replace function public.fpg_reject_project_skill_lock_mutation()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' then
        -- Let the declared project ON DELETE CASCADE clean up child rows while
        -- rejecting direct deletion while the parent project still exists.
        if exists (select 1 from public.projects where id = old.project_id) then
            raise exception 'project skill bindings are immutable' using errcode = '55000';
        end if;
        return old;
    end if;
    raise exception 'project skill bindings are immutable' using errcode = '55000';
end;
$$;

drop trigger if exists project_skill_locks_immutable_trg on public.project_skill_locks;
create trigger project_skill_locks_immutable_trg
before update or delete on public.project_skill_locks
for each row execute function public.fpg_reject_project_skill_lock_mutation();
