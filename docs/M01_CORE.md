# M01 Core developer guide

M01 adds the first production domain behavior while keeping `prototype/` as a
separate executable reference. Postgres is canonical and the API uses raw
Psycopg 3 through `packages/persistence`.

## Local flow

```bash
make bootstrap
make db-reset
make lint
make typecheck
make test
```

`make db-reset` resets the local database, runs pgTAP migration checks, and
runs `tests/integration` against the local Postgres URL. The focused Python
suite can run without a database:

```bash
PYTHONPATH="apps/api/src:packages/domain/src:packages/contracts/src:packages/application/src:packages/model-routing/src:packages/provider-contracts/src:packages/media/src:packages/agent-runtime/src:packages/persistence/src" \
  .venv/bin/python -m pytest tests/python
```

## M01 behavior

- Create projects and allowlisted artifact identities with draft versions.
- Revise with `expected_current_revision`; every revision is a new immutable
  version linked to its parent.
- Transition only through the explicit lifecycle path. Approval and locking
  require human user actors.
- Add upstream-to-downstream edges; cycles and cross-project links fail.
- Approval/lock of a revision creates idempotent descendant impact records by
  traversing from the superseded parent version.
- Resolve impacts or classify validator contradictions without changing
  descendant lifecycle status.
- Approve assets only after a human-attested declared/cleared rights record is
  present with `subject_ref` bound to the exact asset UUID; logical keys never
  authorize another asset.
- Asset versions are append-only; direct mutation/deletion is rejected by SQL,
  while declared parent asset/project cascades clean up their children.
- Persist model/provider/run provenance as JSON without introducing a gateway
  or provider SDK.

No endpoint in this milestone performs a model, media-provider, or external
network call.
