# ADR-009 — M03 Agents Have Read, Propose, and Report Authority Only

## Status

Accepted for M03.

## Decision

The M03 runtime exposes exactly seven application-owned tools:
`read_artifact`, `query_edges`, `retrieve_evidence`, `read_skill_resource`,
`propose_artifact`, `propose_patch`, and `report_finding`.

An agent's effective tools and artifact types are the intersection of application,
agent-role, locked-skill, and project policy. Approval, locking, release, raw SQL,
shell, unrestricted filesystem/network, secrets, provider-policy mutation, and
budget mutation are absent from the registry. Validator authority remains a
trusted system/workflow concern; ordinary M03 agents report typed findings.

Trusted application instructions and locked skill instructions are separated from
labeled untrusted evidence, imported text, comments, provider metadata, and model
output. The tool and output-schema boundary—not prompt wording—enforces authority.

Model calls are resolved through application aliases, checked against immutable
call/cost budgets before execution, and tested only with deterministic fake,
PydanticAI TestModel, or FunctionModel paths. Each result records exact inputs,
skill refs, prompt hash, resolved model, tool calls, retries, usage/cost, structured
output, findings, and disposition in JSON-ready provenance.

## Consequences

- Agent output is always a typed proposal or finding and cannot become canon by
  itself.
- Untrusted text cannot add tools, change schemas/budgets, cross project scope, or
  gain human authority.
- M03 has no live provider configuration and CI makes no external model requests.
- Durable workflow orchestration and M04 creative validators remain deferred.
