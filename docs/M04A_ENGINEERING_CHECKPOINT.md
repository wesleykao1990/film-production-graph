# M04a Story Room engineering checkpoint

This checkpoint implements the deterministic software boundary needed before the
protected M04a product experiment. It does not claim that the Story Room improves
creative quality and it does not record a `PASS`, `MIXED`, `FAIL`, or `INCONCLUSIVE`
product decision.

## Implemented offline

- immutable Story Room values for causal beats, Scene Contracts, scene realizations,
  ordered knowledge changes, reactions, and bounded subtext patches;
- hard validation of objective, opposition, turn, state change, causal fields,
  knowledge continuity, supported facts/entities, patch target/scope/outcome, and
  newly introduced entities;
- a human-only premise selection command that requires an explicit rationale,
  verifies every candidate is a current same-project premise version, approves only
  the selected branch, and preserves alternatives;
- a schema-compatible bridge from exactly 27 complete sample records to the existing
  M04 run-manifest contract, with hard-violation counts derived from typed validator
  reports;
- a rater projection that requires pre-frozen opaque sample, triplet, task, and
  content tokens and rejects source identifiers, condition names, and anchor roles;
- an offline Story Room review route showing candidate review, artifact status,
  matched comparisons, forced-choice instrument tasks, technical-problem handling,
  workload metadata, and preference withholding after instrument failure.
- a provider-neutral protected-generation preflight that binds the supplied protocol
  mapping to its pinned YAML bytes, verifies stage-appropriate hashes and budgets,
  compiles exactly three calibration or 27 primary request descriptors, keeps
  ordinary dry-runs credential-free, and makes no provider call.
- draft calibration, two-rater pilot, operating-characteristic review, and operator
  runbook artifacts that remain visibly incomplete until protected humans fill them.

The analyzer, simulator, shared rule module, protocol schemas, assignments, anchors,
and mechanical examples remain the authoritative evaluation implementation. This
checkpoint does not duplicate their decision rules.

The pre-key operating sequence is documented in
[`M04A_PROTECTED_EXPERIMENT_RUNBOOK.md`](M04A_PROTECTED_EXPERIMENT_RUNBOOK.md).

## Required before M04a can close

The following are protected human/evaluation work and remain incomplete:

1. complete the non-test calibration brief and freeze condition budgets;
2. run the deliberately varied timing/instrument pilot with at least two non-builder
   raters;
3. replace draft/null protocol fields and placeholder references with reviewed,
   hash-pinned values;
4. run the operating-characteristic simulation in `simulate` mode and obtain the
   named human review/signature;
5. generate every frozen primary sample under the three conditions without builder
   selection;
6. collect blinded ratings and forced-choice instrument responses under a supported
   assignment mode;
7. run the authoritative analyzer and immutably record exactly one product decision;
8. when visible dialogue is required, commit the manual speaking-character spike
   evidence described by the milestone protocol.

M04b remains prohibited until M04a records `PASS`.

## Verification

The repository gate exercises strict typing, schema compatibility, lifecycle
authority, complete sample coverage, adversarial blinding checks, analyzer/simulator
fixtures, Studio accessibility contracts, and production builds. All execution is
offline and makes no billable provider calls.
