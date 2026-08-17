# ADR-001 — Workflow Runtime Selection

## Status

Proposed for M05. No durable runtime is selected before M04a PASS and M04b completion.

## Context

The system has low-to-moderate workflow volume, long human approval pauses, external model/media side effects, and Postgres as domain canon. It initially serves a private solo creator but may later become multi-tenant.

## Options

### Simple Postgres jobs/run state

Best when workflows remain short and manually recoverable. Lowest infrastructure cost, but retries, timers, signals, and replay semantics must be built or limited.

### DBOS

Postgres-backed durable execution with a library-oriented deployment model. Attractive when one database and a small service topology are priorities. Sharing a database does not automatically make all external side effects atomic; idempotency and transaction boundaries still require explicit design.

### Temporal

Mature durable workflow semantics, signals, queries, timers, retries, visibility, and replay. Appropriate when workflows span independently deployed services, operations justify the platform, and stable workflow/activity contracts can be maintained.

### Restate

Durable execution and stateful service patterns with a different operational model. Evaluate when service-oriented durable objects or HTTP-centric integration fit the deployment better.

## Decision criteria

Score each option against:

- private versus multi-tenant deployment;
- service count and independent scaling;
- operational ownership;
- human approval duration;
- retry/timer/signal complexity;
- transaction and idempotency needs;
- debugging/visibility requirements;
- migration and contract-evolution burden;
- local development simplicity;
- backup/recovery model.

## Default hypothesis

Choose DBOS for the first private Postgres-centered production tool unless the spike shows missing semantics or unacceptable operational constraints. Preserve a `WorkflowRuntime` interface so Temporal or Restate can replace it without changing domain artifacts or declarative workflow plans.

## Consequences

- Release A has no durable runtime dependency.
- Domain canon never moves into workflow history.
- Runtime-specific payloads are adapters, not core domain contracts.
- Once durable histories exist, public workflow and step identifiers require compatibility discipline.
