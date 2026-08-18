begin;

select plan(8);

select has_table(
    'public', 'project_skill_locks',
    'M02 project skill binding table exists'
);
select has_column(
    'public', 'project_skill_locks', 'snapshot_hash',
    'bindings persist the resolved snapshot hash'
);
select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.project_skill_locks'::regclass
           and conname = 'project_skill_locks_exact_snapshot_key'
    ),
    'one binding per project agent skill and resolved snapshot'
);
select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.project_skill_locks'::regclass
           and pg_get_constraintdef(oid) like '%bound_by_actor_type =%user%'
    ),
    'skill bindings require a human actor type'
);
select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.project_skill_locks'::regclass
           and pg_get_constraintdef(oid) like '%source_commit%'
    ),
    'skill bindings constrain source commits'
);
select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.project_skill_locks'::regclass
           and pg_get_constraintdef(oid) like '%content_hash%'
    ),
    'skill bindings constrain content hashes'
);
select ok(
    exists (
        select 1 from pg_trigger
         where tgrelid = 'public.project_skill_locks'::regclass
           and tgname = 'project_skill_locks_immutable_trg'
    ),
    'skill bindings are append-only'
);
select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.project_skill_locks'::regclass
           and pg_get_constraintdef(oid) like '%project_id%'
    ),
    'skill bindings are project-scoped'
);

select * from finish();
rollback;
