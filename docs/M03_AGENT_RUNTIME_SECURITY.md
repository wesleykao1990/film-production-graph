# M03 Typed Agent Runtime and Security Gate

M03 introduces a typed, least-privilege PydanticAI runtime while keeping every
ordinary test deterministic and offline.

## Runtime boundary

- Four roles are registered: premise candidate, Scene Contract, dialogue patch,
  and continuity critic.
- Tools are limited to typed read, query, retrieve, skill-resource, propose, patch,
  and finding operations.
- Effective permissions are the intersection of application, role, locked-skill,
  and project policies.
- Every read is project-scoped. Skill resources are preloaded only through the
  active exact M02 snapshot and resource allowlist.
- Outputs use strict Pydantic schemas and remain `proposed`; findings do not approve
  or mutate artifacts.
- Immutable model-call and estimated-cost budgets are checked before requests and
  reconciled into provenance.

## Trust framing

Code-reviewed policy, output schemas, tool declarations, locked skill instructions,
and project configuration are trusted. Evidence, imports, comments, provider
metadata, and model output are labeled untrusted data. Prompt labels make the
boundary auditable, while typed tool enforcement remains the security control.

The regression corpus under `tests/security/prompt_injection/` covers instruction
override, self-approval, undeclared tools, cross-project reads, budget escalation,
free-text schema changes, secret requests, shell, filesystem, and network egress.

## Verification

```bash
make check
```

M03 uses only deterministic fake, PydanticAI TestModel, and FunctionModel paths. It
does not add provider credentials, billable calls, durable workflows, or M04 Story
Room behavior.
