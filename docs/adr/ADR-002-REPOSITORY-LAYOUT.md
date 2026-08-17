# ADR-002: M00 repository and workspace layout

- Status: Accepted
- Date: 2026-08-18
- Milestone: M00 Foundation Lite

## Context

The production foundation must remain distinct from the runnable SQLite prototype and must make framework dependencies point inward toward pure code.

## Decision

Use `apps/` for deployable FastAPI and Next.js applications, `packages/` for independently testable Python domain/application contracts, `infra/supabase/` for local Postgres, and root `uv` plus npm workspaces for reproducible commands. Production code may not import `prototype/app`.

## Consequences

The prototype stays an executable reference. M00 contains only scaffolding and ports; canonical artifact behavior begins in M01. A future workflow-runtime package is intentionally absent until M05.

