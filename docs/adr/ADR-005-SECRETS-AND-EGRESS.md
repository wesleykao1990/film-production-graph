# ADR-005: Secrets and ordinary-test egress

- Status: Accepted
- Date: 2026-08-18
- Milestone: M00 Foundation Lite

## Context

Ordinary tests must be safe to run without credentials and must never create billable model or media-provider traffic.

## Decision

Commit only `.env.example`; local `.env` files are ignored. Server-only credentials never use a `NEXT_PUBLIC_` prefix. The ordinary pytest suite rejects non-loopback sockets, CI supplies no provider credentials, and provider/model test paths resolve only deterministic fakes. Real-provider checks belong to explicit protected/manual workflows in later milestones.

## Consequences

Tests that genuinely need external services cannot silently join the default suite. Local Supabase/API integration through loopback remains possible.

