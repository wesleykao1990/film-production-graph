# AI Film Production Graph — Final Build Package v3.0.0

This package is the reviewed implementation handoff for a story-first AI film production system. It combines the final Product Requirements Document, milestone implementation plan, runnable reference prototype, schemas, custom-skill format, experiment tooling, and a ready-to-use initiating prompt for a coding agent.

The governing rule is:

> Typed artifacts in Postgres are canon. Agents propose. Validators block invalid changes. Humans approve. Prompts and media are compiled downstream.

## Four primary entry points

1. [`PRD.md`](PRD.md) — what the product must do and why.
2. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — milestone sequence, tests, and exit gates.
3. [`prototype/README.md`](prototype/README.md) — a runnable local demonstration of the core interaction model.
4. [`INITIAL_PROMPT.md`](INITIAL_PROMPT.md) — the prompt to give a greenfield coding agent.

Use [`prompts/01_EXISTING_REPOSITORY_PROMPT.md`](prompts/01_EXISTING_REPOSITORY_PROMPT.md) instead when integrating with an existing codebase.

## Quick verification

```bash
make bootstrap
make db-reset
make check
```

These commands validate the production M01 core, M02 repository skills, M03 typed
agent security boundary, the M04a offline engineering checkpoint, and the preserved
prototype. See [`docs/M04A_ENGINEERING_CHECKPOINT.md`](docs/M04A_ENGINEERING_CHECKPOINT.md).

Run the prototype:

```bash
cd prototype
python -m uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

## What the prototype demonstrates

The prototype is an executable behavioral specification. It shows:

- immutable artifact payload versions;
- locked canon and explicit human approval;
- evidence/character/beat/scene/screenplay/audio/shot lineage;
- impact records after an upstream revision;
- whole-directory repository-skill hashing;
- a typed `screenplay_patch` proposal;
- a declarative workflow that pauses for human approval;
- zero live model or media-provider calls.

It deliberately uses SQLite, a deterministic mock agent, and a static UI. The
production implementation includes M00 through M03 plus the offline M04a Story Room
engineering checkpoint: hard validators, human premise selection, gate-manifest
projection, and a blinded review fixture. The protected calibration, human-rating
run, and final M04a product decision have not run. There is no workflow engine.

## Build order

```text
Release A — prove story quality
M00 → M01 → M02 → M03 → M04a gate → M04b only after PASS

Release B — prove one film path
M05 → M06 → M07 → M08

Release C — production runtime and studio
M09 → M10

Release D — evaluation and hosted-platform hardening
M11 → M12
```

M00 through M03 and the offline M04a engineering checkpoint are implemented locally.
M04a remains open until its protected human experiment records exactly one product
decision. M04b must not start before a recorded `PASS`.

## Production foundation and M04a engineering checkpoint

The production code lives beside—never inside—the reference prototype. See
[`docs/M00_FOUNDATION.md`](docs/M00_FOUNDATION.md) for the scaffold and local
Supabase setup, and [`docs/M01_CORE.md`](docs/M01_CORE.md) for the canonical
artifact, lineage, impact, rights, and provenance behavior.
Repository-skill behavior is documented in
[`docs/M02_REPOSITORY_SKILLS.md`](docs/M02_REPOSITORY_SKILLS.md).
The typed agent and injection boundary is documented in
[`docs/M03_AGENT_RUNTIME_SECURITY.md`](docs/M03_AGENT_RUNTIME_SECURITY.md).
The Story Room validator, blinding, and remaining human-gate boundary is documented
in [`docs/M04A_ENGINEERING_CHECKPOINT.md`](docs/M04A_ENGINEERING_CHECKPOINT.md).
The pre-credential protected workflow and human evidence packet are documented in
[`docs/M04A_PROTECTED_EXPERIMENT_RUNBOOK.md`](docs/M04A_PROTECTED_EXPERIMENT_RUNBOOK.md).

## Package map

```text
.
├── PRD.md
├── IMPLEMENTATION_PLAN.md
├── INITIAL_PROMPT.md
├── START_HERE.md
├── AGENTS.md
├── FINAL_REVIEW_STATUS.md
├── apps/                      # FastAPI M01 API and Next.js review studio
├── packages/                  # typed domain, application, and persistence packages
├── infra/supabase/            # local database config, migration, seed, and pgTAP
├── prototype/                 # runnable reference implementation
├── docs/                      # architecture and specialist specifications
├── prompts/                   # greenfield, existing-repo, and milestone prompts
├── skills/                    # installable repository skill example
├── workflows/                 # declarative workflow examples
├── schemas/                   # Draft 2020-12 typed contracts
├── examples/                  # golden fixture, real-film skeleton, M04 fixtures
├── scripts/                   # package validation and M04 analysis/simulation
├── templates/
├── machine-readable/
└── research/
```

## Review status

The architecture, sequencing, M04 decision rule, instrument controls, and package mechanics completed five review passes. The final reviewer’s position was to stop adding theoretical controls and proceed to the calibration brief and two-rater pilot. See [`FINAL_REVIEW_STATUS.md`](FINAL_REVIEW_STATUS.md).

## License and rights

This package is an original implementation specification and prototype. Independently verify licenses and release rights before incorporating third-party code, prompts, models, reference media, voices, music, or generated assets.
