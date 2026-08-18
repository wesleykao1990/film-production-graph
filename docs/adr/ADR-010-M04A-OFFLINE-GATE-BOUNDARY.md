# ADR-010 — M04a offline gate boundary

## Status

Accepted for the M04a engineering checkpoint.

## Decision

Keep deterministic Story Room validation in the pure domain layer, human premise
selection in the application layer, and M04 manifest/blinding projection in a thin
application adapter. Continue using `scripts/m4_rules.py` as the sole decision-rule
implementation.

The admin manifest may contain condition and positive-control truth. A rater
projection may contain only pre-frozen opaque labels, triplet/task identifiers,
opaque content tokens, rating dimensions, and allowed response choices. Source
sample, brief, triplet, anchor, condition, and role identifiers are rejected at the
projection boundary.

## Consequences

- Agents still cannot approve, select, lock, unblind, or make the product decision.
- Hard-invalid samples cannot be declared valid by caller-supplied mappings.
- The offline Studio is demonstrative; persistence, authentication, live submissions,
  calibration, human ratings, and the final M04a decision remain separate work.
- M04b stays blocked until the protected M04a process records `PASS`.
