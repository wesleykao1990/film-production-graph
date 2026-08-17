# M02 — Repository Skill Loader

Implement Agent Skills-compatible `SKILL.md`, app-specific `skill.yaml`, schema/resource/permission/budget validation, trigger and adjacent non-trigger tests, path safety, no executable content, content hashing, `skills.lock`, project bindings, and explicit reload.

Git review is the registry. Do not build upload/quarantine/semver dependency services or a marketplace.

Tests: valid load/lock; invalid frontmatter/manifest/schema; path/symlink/executable rejection; hash/lock mismatch; routing; forbidden permission; explicit reload snapshot.

Exit: add and run a new instruction skill without application-code changes, with exact source/hash in provenance.
