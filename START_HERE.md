# Start Here — Final Package v3.0.0

## 1. Choose the handoff path

For a new repository, use [`INITIAL_PROMPT.md`](INITIAL_PROMPT.md).

For an existing repository, first use [`prompts/01_EXISTING_REPOSITORY_PROMPT.md`](prompts/01_EXISTING_REPOSITORY_PROMPT.md) to identify conflicts and map current code to the milestone plan.

## 2. Read these files in order

1. [`PRD.md`](PRD.md)
2. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
3. [`AGENTS.md`](AGENTS.md)
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
5. [`docs/DOMAIN_AND_DATA_MODEL.md`](docs/DOMAIN_AND_DATA_MODEL.md)
6. [`docs/CUSTOM_SKILL_SYSTEM.md`](docs/CUSTOM_SKILL_SYSTEM.md)
7. [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
8. [`prototype/README.md`](prototype/README.md)

Read [`docs/M4_EXPERIMENT_PROTOCOL.md`](docs/M4_EXPERIMENT_PROTOCOL.md) before implementing M03 or M04.

## 3. Verify the package

```bash
make bootstrap
make db-reset
make check
```

This verifies the M01 production core, M02 repository skills, and the preserved
prototype. M02 behavior is documented in
[`docs/M02_REPOSITORY_SKILLS.md`](docs/M02_REPOSITORY_SKILLS.md).

The checked-in M04 analysis outputs are mechanical fixtures, not evidence that the product thesis has passed.

## 4. Inspect the prototype before coding

Run:

```bash
cd prototype
python -m uvicorn app.main:app --reload --port 8000
```

Use it to understand the intended behavior:

1. inspect locked artifacts and lineage;
2. run the subtext workflow;
3. confirm the output remains `proposed`;
4. approve it through a separate human action;
5. revise the Scene Contract;
6. inspect descendant impact records.

The prototype is not the production foundation. Do not port its SQLite repository, lack of authentication, or mock execution into the real implementation.

## 5. Initial delivery assumptions

```yaml
builder: solo_builder_with_coding_agents
initial_mode: private_or_personal_production_tool
first_film_duration: 60_to_180_seconds
first_film_characters: 2_to_3
first_film_locations: 1_to_2
first_priority: prove_story_quality
second_priority: finish_one_watchable_film
future_option: productize_only_after_both_gates_pass
```

## 6. Non-negotiable product rules

1. Postgres and typed contracts are canon.
2. Agents propose; humans or explicit policy approve.
3. Locked payload versions are immutable.
4. Impact records are separate from lifecycle state.
5. Provider prompts may not introduce story facts.
6. Evidence is untrusted data; reviewed repository skills are instruction dependencies.
7. Audio identity, music cues, ambience, SFX, subtitles, rights, costs, and delivery requirements are first-class.
8. Music is sequence/scene/timeline-level, never independently generated per shot.
9. Skills are pinned by Git source and whole-directory hash.
10. Ordinary tests make no billable model or provider calls.
11. The cheapest coherent representation is approved before expensive generation.
12. One milestone is implemented and proven at a time.

## 7. Release sequence

```text
Release A — does it write better?
M00   Foundation Lite
M01   Canonical artifacts, lineage, impact, and rights basics
M02   Repository skill loader and skills.lock
M03   Typed agent runtime and early security gate
M04a  Minimum Story Room plus executable decision gate
       ── PASS / MIXED / FAIL / INCONCLUSIVE ──
M04b  Remaining creative passes and export, only after PASS

Release B — can it become a film?
M05   WorkflowRuntime ADR and durable approvals
M06   Audio, delivery, subtitles, rights, and cost ledger
M07   Shot Contracts, storyboard, animatic, and dialogue path
M08   Manual provider adapter and minimum finished-film path

Release C — can production scale without losing control?
M09   Production provider adapters
M10   Full studio, editing, OTIO, and release provenance

Release D — can it become a hosted product?
M11   Evaluation, observability, and regression gates
M12   Hosted skills, multi-tenancy, security, deployment, and recovery
```

## 8. Continue the milestone sequence

M00 through M02 are implemented locally. Continue with M03 only after reviewing
the M02 exit-gate evidence and M03 security boundary.
