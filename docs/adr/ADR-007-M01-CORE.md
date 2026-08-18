# ADR-007 — M01 Canonical Artifact, Lineage, Impact, and Rights Core

## Status

Accepted for M01.

## Decision

M01 uses a narrow Psycopg 3 repository over Supabase/Postgres. The domain and
application packages remain independent of FastAPI, Psycopg, Supabase client
libraries, provider SDKs, and the prototype. SQL migrations own relational
constraints; application services own command validation and actor authority.

Artifact identities and immutable payload versions are separate rows. A
revision takes an expected current revision, points to its superseded parent,
and inserts a new version. The payload, content hash, revision, parent, actor,
and creation timestamp cannot be updated. Locked rows reject every update.
Lifecycle transitions are explicit: `draft → validated → human_review →
approved → locked`, with `human_review → rejected`. Approval and locking
require an actor of type `user`; agents can only create drafts.

Edges point from upstream (`from_version_id`) to downstream
(`to_version_id`). Postgres and the in-memory contract adapter reject
cross-project links and cycles. Approving or locking a revision walks from its
superseded parent through downstream edges and inserts idempotent impact rows
for reachable descendants. Impact classification/resolution never changes an
affected artifact lifecycle.

Asset approval requires a human-attested rights record in `declared` or
`cleared` state with a holder, permitted uses, territories, reviewer, and
review time. The rights `subject_ref` must equal the exact asset UUID; an asset
logical key is never an approval binding. Asset-version rows are append-only:
SQL rejects direct updates/deletes but permits the declared parent
asset/project cascade cleanup. Run provenance is retained as typed JSON
in `run_records` until later milestones need normalized run-input/tool tables.

## Consequences

- Postgres is the production source of truth; no ORM is introduced.
- The API can remain healthy without credentials while commands return an
  explicit service-unavailable response when persistence is not configured.
- M01 tests can exercise all authority and graph rules with a deterministic
  in-memory adapter; Postgres tests run when `FPG_DATABASE_URL` is supplied.
- RLS, memberships, provider operations, costs, workflow durability, and
  payload-specific story schemas remain later-milestone work.
