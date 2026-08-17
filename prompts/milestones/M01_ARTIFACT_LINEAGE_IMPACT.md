# M01 — Artifact, Lineage, Impact, and Rights Core

Implement immutable artifact identities/versions, lifecycle transitions, edges, impact records, approvals, human decisions, assets, rights records, run provenance, canonical hashing, optimistic concurrency, and coarse descendant reachability.

Do not use `stale` as lifecycle state. Upstream changes create impact rows. Asset approval requires a rights block.

Tests: locked mutation rejection; revision/concurrency; edge cycles; reachable impacts only; lifecycle unchanged; contradiction classification; bulk resolution; stable hashes; cross-project link rejection; rights gate.

Exit: lock constitution/evidence/sequence/Scene Contract, revise upstream, inspect and resolve impacts, trace lineage both directions.
