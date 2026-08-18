# ADR-008 — M02 Repository Skills Are Immutable Reviewed Snapshots

## Status

Accepted for M02.

## Decision

Repository skills are data-only reviewed packages. The loader discovers configured
roots, validates portable and app metadata separately, rejects executable or unsafe
content, and verifies whole-directory hashes in `skills.lock`.

A successful explicit reload atomically replaces an immutable process snapshot;
failure preserves the active snapshot. Projects bind agents to exact path, Git
commit SHA, content hash, metadata version, and snapshot hash values. Run provenance
repeats that resolved reference. Git review is the registry, and skill content is
never imported or executed.

Bindings are append-only versions. The latest `(created_at, id)` record is current;
an explicit human rebind after reload adds a row and preserves older provenance.

## Consequences

- Any reviewed package change requires a new digest and explicit reload.
- A project binding cannot silently float to changed content.
- Humans bind and reload skills; a fake run may be agent-attributed but invokes no
  provider.
- Marketplace, upload/quarantine, dependency resolution, and executable sandboxing
  remain deferred.
