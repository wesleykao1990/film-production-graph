begin;

select plan(2);

select has_table(
    'fpg_meta',
    'foundation_marker',
    'M00 bootstrap marker exists'
);

select results_eq(
    $$ select milestone from fpg_meta.foundation_marker where singleton = true $$,
    array['M00'::text],
    'M00 seed is repeatable'
);

select * from finish();
rollback;

