# ADR-003: Canonical hashing boundary

- Status: Accepted
- Date: 2026-08-18
- Milestone: M00 Foundation Lite

## Context

Later milestones require stable artifact, skill, prompt, and asset hashes. Inventing multiple serializers would make lineage and reproducibility unreliable.

## Decision

Treat the existing schema documents and `docs/DOMAIN_AND_DATA_MODEL.md` hashing rules as normative. UTF-8, Unicode normalization, sorted keys, stable number and line-ending rules, and explicit exclusion of transient fields will be implemented once in the pure contracts/domain boundary during M01. Whole-skill-directory hashing remains governed separately by `docs/CUSTOM_SKILL_SYSTEM.md`.

## Consequences

M00 does not create an incomplete artifact hasher. Test fakes may have deterministic IDs, but those identifiers are not presented as canonical production hashes.

