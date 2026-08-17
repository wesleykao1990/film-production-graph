# Workflow Runtime Specification — Final reviewed specification

## 1. Objective

Keep workflow semantics application-owned and runtime-independent. Do not require a durable engine before M04a PASS and M04b completion.

## 2. Phases

### M00–M04b

Execute small workflows synchronously or through simple recorded background jobs. Persist run inputs, outputs, state, and approvals in Postgres. Avoid pretending this is fully durable.

### M05+

Interpret immutable `WorkflowPlan` objects through a selected `WorkflowRuntime` adapter.

## 3. Runtime interface

```python
class WorkflowRuntime(Protocol):
    async def start(self, plan: WorkflowPlan, context: RunContext) -> RunRef: ...
    async def signal(self, run_id: str, signal: WorkflowSignal) -> None: ...
    async def query(self, run_id: str) -> WorkflowState: ...
    async def cancel(self, run_id: str, reason: str) -> None: ...
```

## 4. Allowed step types

- `agent_run`
- `validator`
- `transform`
- `human_approval`
- `fan_out`
- `join`
- `provider_task`
- `media_job`
- `emit_artifact`

Arbitrary Python expressions, shell commands, and dynamic code imports are forbidden.

## 5. Plan model

A normalized plan contains:

```text
plan ID/version/hash
input/output contracts
ordered step definitions
needs/dependencies
skill refs
capability refs
budgets
timeouts/retries
approval policy
bounded revision routes
```

The compiler rejects cycles except explicitly bounded revision routes.

## 6. Determinism and side effects

Regardless of runtime:

- model/provider/media/database side effects occur through idempotent activities/tasks;
- external request idempotency keys are derived from run/step/input hashes;
- artifact emission uses unique constraints;
- callbacks are deduplicated;
- workflow state contains IDs/hashes, not large media;
- Postgres domain artifacts remain canon.

Using the same Postgres database for runtime checkpoints and domain state does not automatically make external side effects atomic. Explicit transaction and reconciliation logic remains required.

## 7. Runtime selection

M05 executes `ADR-001-WORKFLOW-RUNTIME.md`.

Default hypothesis:

- DBOS for private Postgres-centered deployment;
- Temporal for complex multi-service operations and mature visibility/replay needs;
- Restate when its stateful-service model better fits;
- simple Postgres jobs if workflows remain limited.

## 8. Human approval protocol

An approval request stores:

```text
run/step ID
artifact versions under review
review policy
requested actor/role
deadline
default timeout behavior
```

Signals are idempotent. Agents cannot emit approval signals. Duplicate or late decisions are recorded but do not repeat downstream work.

## 9. Failure states

```text
retryable_external
non_retryable_contract
budget_exceeded
permission_denied
human_rejected
cancelled
timeout
manual_intervention_required
```

Local repair receives the finding and bounded edit scope rather than restarting the entire plan.

## 10. Tests

Every runtime adapter passes the same contract suite:

- start/query/signal/cancel;
- interruption and resume;
- duplicate signal;
- activity retry;
- idempotent provider/artifact side effect;
- approval timeout;
- bounded repair loop;
- failure between external response and persistence;
- backup/restore or runtime-specific recovery;
- compatibility/replay where applicable.
