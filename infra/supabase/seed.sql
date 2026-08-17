insert into fpg_meta.foundation_marker (singleton, milestone, schema_version)
values (true, 'M00', 1)
on conflict (singleton) do update
set milestone = excluded.milestone,
    schema_version = excluded.schema_version;

