# M05 — WorkflowRuntime ADR and Durable Approvals

Precondition: M04a PASS and M04b complete.

Execute ADR-001 by comparing simple Postgres jobs, DBOS, Temporal, and Restate for the actual deployment. Implement `WorkflowRuntime` and one selected adapter, immutable plans, idempotent tasks, approvals/signals, retries, cancellation, timeouts, bounded repairs, and reconciliation.

Do not move narrative canon into workflow history.

Exit: interrupt during approval, restart, approve, and finish with no duplicate external call or artifact.
