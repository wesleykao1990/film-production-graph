# Runnable Reference Prototype

This prototype is included so the package is more than a collection of documents. It demonstrates the intended interaction and authority model with a deterministic local application.

## What it proves

- canonical artifacts have immutable payload versions;
- a revision creates a new version rather than overwriting a locked one;
- lineage edges connect evidence, characters, beats, Scene Contracts, screenplay, audio, and shots;
- revising an upstream artifact creates separate `impact_record` rows for reachable descendants;
- repository skills are discovered from `skills/*`, parsed, permission-scoped, and hashed across the whole directory;
- a mock agent can create a typed `screenplay_patch` proposal;
- the agent cannot approve its own output;
- a declarative workflow pauses at `human_approval`;
- accepted and pending artifacts remain visible in lineage;
- no external model or provider call is needed.

## What it deliberately does not prove

This is **not** the production foundation. It uses SQLite, a deterministic fake agent, and a static browser UI. It has no authentication, Supabase RLS, durable workflow runtime, provider API, media rendering, or multi-user collaboration.

The real implementation remains the M00–M12 plan:

- Next.js + TypeScript review studio;
- FastAPI + Python application API;
- Supabase Postgres as canon;
- PydanticAI with application-owned tools;
- repository skills pinned by Git and whole-directory hash;
- FFmpeg/ffprobe media utilities;
- a durable runtime only after the Story Room gate passes.

Do not copy the SQLite persistence layer into production merely because it is convenient. Treat the prototype as an executable behavioral specification.

## Run it

```bash
cd prototype
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pytest
python -m uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

Equivalent Make targets:

```bash
make install
make test
make dev
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

## Suggested demo

1. Inspect the locked Creative Constitution and Scene Contract.
2. Select **Run subtext workflow**.
3. Inspect the new `screenplay_patch`: it is `proposed`, not approved.
4. Select **Approve proposed patch** and confirm the human decision is recorded.
5. Select **Revise scene contract**.
6. Observe that the prior locked version remains, a new draft version appears, and descendants receive impact records.
7. Approve and lock the new Scene Contract through separate human actions.

## Add a custom skill

Create a new directory under the package-level `skills/` folder:

```text
skills/my-film-method/
  SKILL.md
  skill.yaml
  references/
  schemas/
  tests/
```

The prototype discovers and hashes it on restart. Unknown skills are still listed and can produce a safe `critic_finding` in mock mode. The production M03 agent runtime will load the same package as an instruction skill and execute it through typed, permission-checked model calls.

The portable method belongs in `SKILL.md`. Application permissions, input/output contracts, budgets, and activation stage belong in `skill.yaml`. Arbitrary uploaded Python or shell code remains prohibited.

## Reset and inspect

```bash
python -m app.cli reset
python -m app.cli smoke
python -m app.cli show
```
