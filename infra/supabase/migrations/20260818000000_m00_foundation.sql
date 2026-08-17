-- M00 migration proof only. Canonical artifact tables begin in M01.
create schema if not exists fpg_meta;

create table if not exists fpg_meta.foundation_marker (
    singleton boolean primary key default true check (singleton),
    milestone text not null check (milestone = 'M00'),
    schema_version integer not null check (schema_version > 0)
);

comment on table fpg_meta.foundation_marker is
    'Bootstrap marker only; this is not an artifact or production-domain table.';

