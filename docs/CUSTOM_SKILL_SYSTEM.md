# Custom Skill System — Final reviewed specification

## 1. Objective

Allow creators to add filmmaking methods and declarative workflows without application-code changes, while avoiding a hosted package-manager subsystem before the Story Room is validated.

## 2. Release A source model

Git is the registry:

```text
source = repository path + commit SHA + whole-package content hash
review = pull request
immutability = commit/hash
pinning = skills.lock
security review = code review + deterministic validation
```

A hosted registry is M12 work.

## 3. Skill tiers

### Tier A — Instruction skill

Markdown procedure plus resources/schemas/tests. No executable scripts.

### Tier B — Declarative workflow skill

A validated YAML plan using allowed step types. It references Tier A skills and registered capabilities.

### Tier C — Executable capability

Reviewed/deployed application code implementing a provider, parser, validator, media analyzer, or exporter. It is not runtime-uploaded content.

## 4. Folder format

```text
skills/subtext-pass/
  SKILL.md
  skill.yaml
  schemas/
    input.schema.json
    output.schema.json
  references/
    method.md
  tests/
    trigger_cases.yaml
    contract_cases.yaml
```

## 5. Portable `SKILL.md`

Use portable Agent Skills frontmatter for identity and routing description:

```yaml
---
name: subtext-pass
description: >
  Reduces direct exposition while preserving scene objective, outcome,
  knowledge state, and character voice. Use after dialogue drafting.
license: CC0-1.0
compatibility: film-production-graph
metadata:
  version: "1.0.0"
  film-production-graph-api: "v1"
---
```

`name` and `description` stay top-level. The description is the router for `activation: auto`, so routing tests are description-quality tests.

Do not put application-private tools such as `read_artifact` in portable `allowed-tools`. They have no meaning in unrelated hosts and would be decorative. `skill.yaml` is the enforced authority source.

## 6. App-specific `skill.yaml`

```yaml
activation: auto
stage: screenplay_revision

contracts:
  input: schemas/input.schema.json
  output: schemas/output.schema.json

permissions:
  artifacts:
    read: [scene_contract, screenplay_scene, character, relationship]
    propose: [screenplay_patch, critic_finding]
  tools: [read_artifact, read_skill_resource, propose_patch]
  providers: [llm]
  network_hosts: []
  shell: false
  media: false

resources:
  allow:
    - references/method.md

budgets:
  max_model_calls: 3
  max_cost_usd: 1.00

tests:
  routing: tests/trigger_cases.yaml
  contracts: tests/contract_cases.yaml
```

Do not duplicate portable name/version fields in `skill.yaml`.

## 7. Whole-package hashing and `skills.lock`

The content hash covers every regular file in the skill directory:

```text
SKILL.md
skill.yaml
schemas/**
references/**
tests/**
any other reviewed resource
```

Canonical algorithm:

1. reject symlinks and executable files;
2. enumerate all regular files under the skill root;
3. exclude only documented transient files such as `.DS_Store`, `__pycache__`, and editor swap files;
4. sort normalized POSIX relative paths bytewise;
5. hash each path, byte length, and exact file bytes with unambiguous separators;
6. prefix the final digest with `sha256:`.

A change to `references/method.md` must invalidate the lock even when `SKILL.md` is unchanged.

```yaml
lock_version: 1
skills:
  subtext-pass:
    source_path: skills/subtext-pass
    source_commit: abcdef123456
    content_hash: sha256:...
    metadata_version: 1.0.0
```

The runtime refuses a package whose content does not match the lock. Explicit reload creates a new resolved skill-set hash for future runs; historical runs remain bound to prior hashes.

## 8. Validation

Release A loader validates:

- required portable fields;
- app manifest schema;
- input/output schemas;
- referenced files remain inside the skill directory;
- no symlinks or executable files;
- file count/size limits;
- allowed tools/artifact types/providers from `skill.yaml`;
- budgets;
- trigger and adjacent non-trigger cases;
- contract fixtures;
- whole-package content hash and lock.

No archive extraction is needed in Release A.

## 9. Permissions

Permissions are an intersection:

```text
application maximum
∩ agent role
∩ skill manifest
∩ project policy
= effective permissions
```

A skill cannot request approval, locking, raw SQL, shell, unrestricted filesystem, secrets, or arbitrary network access.

## 10. Routing tests

A routing suite contains positive, negative, and adjacent-skill negative examples. Auto-routing is disabled for a skill that cannot pass its routing suite at the configured threshold.

## 11. Workflow skill format

Allowed step types:

```text
agent_run
validator
transform
human_approval
fan_out
join
provider_task
media_job
emit_artifact
```

A compiler validates DAG structure, contracts, permissions, bounded loops, and references, then emits an immutable `WorkflowPlan` hash. Release A may execute plans synchronously. M05 executes them through `WorkflowRuntime`.

## 12. Hosted registry in M12

Only after product validation add upload/quarantine, immutable semantic versions, dependency resolution, organization scopes, upgrade/revocation, author audit, and isolated executable-capability deployment. The package format remains compatible with Release A.
