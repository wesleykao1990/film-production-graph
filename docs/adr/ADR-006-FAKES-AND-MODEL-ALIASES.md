# ADR-006: Deterministic fakes and application model aliases

- Status: Accepted
- Date: 2026-08-18
- Milestone: M00 Foundation Lite

## Context

Release A needs typed agent development without provider lock-in, live credentials, or a premature gateway service.

## Decision

Application configuration owns semantic model aliases. Resolution records the alias plus the explicit fake provider/model in M00. Provider-neutral ports receive deterministic in-process fakes for tests. PydanticAI is available to production Python code, but M00 adds neither a real-provider package nor a gateway.

## Consequences

Tests are stable and non-billable. Direct real-model resolution can be added behind the same application boundary in M03, with complete provenance and permission enforcement.

