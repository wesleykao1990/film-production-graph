# Repository-Wide Coding Agent Contract — Final v3.0.0

This file governs all automated coding work in the Film Production Graph repository.

## Mission

Implement a story-first, versioned AI-film production system while preserving authorship, human control, provider independence, audio continuity, rights, delivery constraints, reproducibility, and complete lineage.

## Required reading

Before changing code, read:

1. `START_HERE.md`
2. `PRD.md`
3. `IMPLEMENTATION_PLAN.md`
4. `prototype/README.md`
5. `docs/IMPLEMENTATION_PLAN.md`
6. `docs/M4_EXPERIMENT_PROTOCOL.md` when working on M03, M04a, or M04b
7. the current milestone prompt
8. relevant schemas, examples, and ADRs

## Scope discipline

- Implement only the named milestone.
- Do not start later infrastructure “for convenience.”
- Prefer the smallest complete vertical slice satisfying the exit gate.
- Record deviations in an ADR or issue.
- Stop after demonstrating the current exit gate.
- Do not build the full production platform before M04a passes.
- Keep `prototype/` green, but do not use its SQLite/static/mock implementation as production architecture.

## Non-negotiable invariants

1. Typed immutable artifact versions in Postgres are canonical.
2. Agents create proposals, patches, and findings; they cannot approve or lock.
3. Locked artifact versions are never updated in place.
4. Upstream changes create separate `impact_record` entries; lifecycle state and impact state are not conflated.
5. Prompt compilers cannot introduce facts absent from locked/snapshotted contracts.
6. Provider-specific data stays outside core domain contracts.
7. Audio policy is explicit per shot; picture replacement cannot silently replace approved soundtrack state.
8. Music is attached to a sequence, scene, or timeline cue—not generated independently per shot.
9. Release A skills are repository assets pinned by Git source and content hash.
10. Runtime-installed arbitrary code is prohibited.
11. Untrusted evidence cannot add tools, elevate authority, cross project boundaries, change budgets, or approve output.
12. Every asset has a rights block before approval and must be cleared for the intended release use.
13. A locked Delivery Specification controls export validation.
14. Ordinary tests perform zero billable model or media-provider calls.
15. Every generated or imported artifact records provenance, including unknown fields honestly.

## Release-specific rules

### Before the M04a gate

- Do not introduce Temporal, DBOS, Restate, a workflow server, or a LiteLLM gateway service.
- Use application-owned model aliases and recorded resolved model IDs.
- Use synchronous/background execution sufficient for the experiment.
- Keep skills in the repository and use a whole-directory `skills.lock`; changing a reference or test must invalidate the lock.
- Do not implement M04b features inside M04a.
- Before M04a freeze, require `analyze_m4.py` and `simulate_m4.py` to share `m4_rules.py`, run calibration-informed operating-characteristic scenarios, and obtain a named human review.
- Do not reduce judgments per triplet to solve a timing problem; recruit the seventh rater or shorten the rated scene within the frozen range.
- Run the manual visible-dialogue spike in parallel with M04a when applicable, record attempts to first acceptable take, but do not build a provider adapter for it.

### After M04a PASS and M04b completion

- Implement `WorkflowRuntime` behind an interface.
- Select DBOS, Temporal, Restate, or a simpler runtime through the ADR criteria—not preference.
- Preserve stable public workflow/step identifiers after durable histories exist.

## Engineering rules

- Keep domain models independent of FastAPI, UI, workflow runtime, and providers.
- Use one migration system.
- Place business rules in domain/application services, not route handlers.
- Use narrow tools rather than raw SQL, shell, unrestricted filesystem, or unrestricted network access.
- Keep approval commands separate from agent tools.
- Make provider callbacks and side-effecting jobs idempotent.
- Prefer additive contract evolution; version incompatible changes.
- Record exact model, provider, skill, prompt bundle, schema, and code versions.
- Treat imported text, media metadata, model output, and provider callbacks as untrusted.

## Testing rules

Every feature requires:

- unit tests;
- at least one failure-path test;
- contract/integration tests for boundaries;
- documentation updates;
- intentional fixture updates only.

For probabilistic behavior:

- test schemas, permissions, invariants, routing, budgets, provenance, and hard validators deterministically;
- use fake/test models on pull requests;
- run real-model and human evaluation only in protected/manual workflows;
- never assert exact model prose.

Security tests begin in M03, not at the end. An evidence item containing an instruction to approve itself must be unable to alter the output schema, invoke undeclared tools, obtain approval, exceed budget, or access another project.

## Completion report

Return:

1. behavior implemented;
2. files changed;
3. migrations and public contracts changed;
4. commands/tests run with results;
5. exit-gate evidence;
6. security, compatibility, cost, rights, and migration considerations;
7. known limitations;
8. exact next dependencies.

Do not claim completion without exit-gate evidence.
