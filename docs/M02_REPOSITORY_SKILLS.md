# M02 Repository Skill Loader developer guide

M02 makes reviewed repository skills a production dependency without executing
package code. Git remains the registry: a skill is loaded only from a configured
repository root and when its complete directory matches `skills.lock`.

## Configuration

```bash
FPG_REPOSITORY_ROOT=/absolute/path/to/the/repository
FPG_SKILL_ROOTS=skills
FPG_SKILLS_LOCK=skills.lock
```

When configured, the API validates and snapshots packages at startup. Disk changes
remain invisible until a human calls the explicit reload endpoint.

## Safety and validation

- `SKILL.md` owns portable identity and routing text; `skill.yaml` owns app
  contracts, resources, permissions, providers, budgets, and test locations.
- Schemas, resource paths, routing cases, and contract fixtures are validated.
- Traversal, symlinks, executable bits, shebangs, script extensions, shell access,
  network hosts, unknown providers, and authority-bearing tools are rejected.
- Defaults cap packages at 128 files, 1 MiB per file, and 8 MiB total.
- Whole-package hashing covers every sorted POSIX path, byte length, and exact bytes.
- Production `source_commit` values are lowercase 7–40 character Git SHAs.

## API flow

1. `GET /api/skills` inspects the immutable snapshot.
2. `POST /api/skills/reload` atomically reloads it and requires a human actor.
3. `POST /api/projects/{project_id}/skill-bindings` binds an agent to the exact
   path, commit, package hash, metadata version, and snapshot hash. Rebinding after
   reload appends a new exact version while preserving binding history.
4. `POST /api/projects/{project_id}/skills/{skill_name}/fake-run` verifies that
   binding and records the exact values in run provenance.

The fake run performs no model, provider, shell, or package-code execution. It is
the M02 exit proof, not the M03 typed agent runtime.

## Verification

```bash
make db-reset
make check
```

M02 does not add workflow execution, provider adapters, uploads, quarantine,
dependency resolution, hosted registries, or a marketplace.
