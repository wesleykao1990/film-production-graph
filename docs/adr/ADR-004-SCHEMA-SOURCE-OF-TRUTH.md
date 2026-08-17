# ADR-004: Contract schema source of truth

- Status: Accepted
- Date: 2026-08-18
- Milestone: M00 Foundation Lite

## Context

Python, TypeScript, database, and provider boundaries will eventually share typed contracts.

## Decision

Draft 2020-12 JSON Schemas under `schemas/` are the committed interchange source of truth. Pure Python contract models may validate or represent those contracts, and generated TypeScript types must be reproducible derivatives. Database migrations enforce persistence constraints but do not redefine interchange payloads.

## Consequences

Schema validation remains in ordinary CI. Hand-maintained duplicate TypeScript payload interfaces are avoided once generation begins; incompatible contract changes require a schema-version change.

