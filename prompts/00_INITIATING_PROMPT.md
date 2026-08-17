# Initial Prompt — Greenfield Build

You are the lead implementation agent for **Film Production Graph**.

This repository contains a final reviewed specification and a runnable reference prototype. The prototype is an executable behavioral example, not the production persistence or runtime implementation.

## Read in this order

1. `START_HERE.md`
2. `PRD.md`
3. `IMPLEMENTATION_PLAN.md`
4. `AGENTS.md`
5. `docs/ARCHITECTURE.md`
6. `docs/DOMAIN_AND_DATA_MODEL.md`
7. `docs/TEST_STRATEGY.md`
8. `prototype/README.md`
9. `prompts/milestones/M00_FOUNDATION_LITE.md`

Before changing production code:

```bash
python scripts/validate_package.py
cd prototype
python -m pip install -e ".[dev]"
python -m pytest
python -m app.cli smoke
```

Inspect the prototype interaction model, then return to the repository root.

## Implement M00 Foundation Lite only

Create the production monorepo foundation described in the M00 milestone prompt. Use the reviewed target stack:

- Next.js + TypeScript minimal review studio;
- FastAPI + Python API;
- pure domain and contract packages;
- Supabase local Postgres migration and seed path;
- PydanticAI test dependencies and fake model/provider implementations;
- application-owned model aliases;
- FFmpeg/ffprobe environment checks;
- one-command bootstrap, development, database reset, lint, typecheck, and test commands;
- network guard proving ordinary tests make no live model/provider request;
- CI and required ADRs.

## Product invariants

- Typed immutable Postgres artifact versions are canon.
- Agents create proposals, patches, and findings; they cannot approve or lock.
- Locked payload versions are never updated in place.
- Impact records are separate from lifecycle state.
- Provider prompts may express approved facts but cannot introduce new story facts.
- Audio, rights, delivery, subtitles, cost, and provenance are first-class.
- Repository skills are pinned by Git source and whole-directory content hash.
- Evidence and imported content are untrusted and cannot gain tool or approval authority.
- Ordinary tests perform zero billable model or media-provider calls.

## Prototype boundary

Do not port the prototype’s SQLite repository into the production implementation. Do not treat its static UI, mock agent, or non-durable workflow loop as milestone completion. Preserve its observable behavior where it reflects a product invariant, but implement M00 using the production architecture and milestone contracts.

Do not modify or delete `prototype/`; keep its tests passing as a reference suite.

## Prohibited M00 scope

Do not introduce:

- Temporal, DBOS, Restate, or another durable workflow service;
- a LiteLLM gateway service;
- a hosted skill registry;
- real LLM, video, image, TTS, music, SFX, or lip-sync integrations;
- the complete artifact domain;
- a full lineage graph editor;
- GraphRAG, Neo4j, Kubernetes, or custom model training.

## Required completion report

Run all M00 checks from a clean state. Return:

1. behavior implemented;
2. files and public contracts changed;
3. migrations and ADRs created;
4. commands executed and exact results;
5. M00 exit-gate evidence;
6. security, compatibility, and migration considerations;
7. known limitations;
8. exact M01 prerequisites.

Stop after M00. Do not continue to M01.
