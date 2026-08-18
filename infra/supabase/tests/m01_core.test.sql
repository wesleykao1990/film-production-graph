begin;

select plan(16);

select has_table('public', 'projects', 'M01 projects table exists');
select has_table('public', 'artifact_identities', 'artifact identities table exists');
select has_table('public', 'artifact_versions', 'artifact versions table exists');
select has_table('public', 'artifact_edges', 'artifact edges table exists');
select has_table('public', 'impact_records', 'impact records table exists');
select has_table('public', 'assets', 'assets table exists');
select has_table('public', 'rights_records', 'rights records table exists');
select has_column(
    'public', 'rights_records', 'attested_by_actor_type',
    'rights records persist attesting actor type'
);
select has_column(
    'public', 'rights_records', 'attested_by_actor_id',
    'rights records persist attesting actor id'
);

select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.impact_records'::regclass
           and conname = 'impact_records_cause_version_id_affected_version_id_key'
    ),
    'impact pairs are unique'
);
select ok(
    exists (
        select 1 from pg_trigger
         where tgrelid = 'public.artifact_versions'::regclass
           and tgname = 'artifact_versions_immutable_trg'
    ),
    'artifact payload immutability trigger exists'
);
select ok(
    exists (
        select 1 from pg_trigger
         where tgrelid = 'public.asset_versions'::regclass
           and tgname = 'asset_versions_immutable_trg'
    ),
    'asset versions are append-only'
);
select ok(
    exists (
        select 1 from pg_trigger
         where tgrelid = 'public.artifact_edges'::regclass
           and tgname = 'artifact_edges_cycle_trg'
    ),
    'artifact cycle trigger exists'
);
select ok(
    exists (
        select 1 from pg_trigger
         where tgrelid = 'public.assets'::regclass
           and tgname = 'assets_rights_gate_trg'
    ),
    'asset rights gate trigger exists'
);
select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.approvals'::regclass
           and pg_get_constraintdef(oid) like '%actor_type =%user%'
    ),
    'approval actor is human-only'
);
select ok(
    exists (
        select 1 from pg_constraint
         where conrelid = 'public.rights_records'::regclass
           and pg_get_constraintdef(oid) like '%attested_by_actor_type%user%'
    ),
    'declared/cleared rights require a human attester'
);

select * from finish();
rollback;
