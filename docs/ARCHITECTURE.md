# Architecture Specification — Final reviewed specification


## Reference prototype boundary

`prototype/` is an executable behavioral specification for canon, lineage, impact, repository skills, typed proposals, and human approval. It intentionally uses SQLite, a deterministic mock agent, and static assets so it can run without credentials. Production code must preserve the demonstrated authority and versioning behavior while replacing persistence, UI, security, and runtime components according to the milestones. No production dependency may import from `prototype/app`.

## 1. Objective

Build the smallest architecture that can prove the creative thesis, finish one film, and later expand without replacing canon.

```text
Creative Constitution + Evidence
              ↓
       Story artifacts
              ↓
     Human-approved canon
              ↓
   Scene/sequence/shot/audio contracts
              ↓
       Compiled provider bundles
              ↓
  Generation attempts and manual imports
              ↓
       Timeline, subtitles, release
```

Postgres owns domain truth. Agents, workflow runtimes, providers, vector retrieval, and UIs are replaceable execution or presentation layers.

## 2. Release A logical architecture

```text
┌──────────────────────────────┐
│ Next.js Minimal Review UI    │
│ forms, diffs, blind ratings  │
└──────────────┬───────────────┘
               │
             FastAPI
               │
       ┌───────┴───────────┐
       │                   │
 Supabase Postgres     Agent Runtime
 canonical artifacts   PydanticAI
 edges/impacts         narrow tools
 approvals/ratings     fake or direct models
       │                   │
       └───────┬───────────┘
               │
       repository skills
       SKILL.md + skill.yaml
               │
          FFmpeg/ffprobe
```

Release A has no Temporal/DBOS/Restate service and no LiteLLM gateway service.

## 3. Repository architecture

```text
apps/
  studio-web/
  api/

packages/
  domain/              # pure models and rules
  contracts/           # JSON Schema and generated TS types
  application/         # use cases and ports
  agent-runtime/       # PydanticAI, tools, skill loading
  model-routing/       # aliases and resolved-model recording
  media/               # FFmpeg wrappers and validation
  provider-contracts/  # provider-neutral interfaces
  workflow-runtime/    # introduced after M4

skills/
  ...
skills.lock

infra/
  supabase/

tests/
  fixtures/
  security/
  evals/
```

Frameworks depend inward on domain/application contracts. The domain package imports neither FastAPI, PydanticAI, a workflow runtime, Supabase client code, nor provider SDKs.

## 4. Canonical artifact model

An artifact version contains:

```text
identity
project and artifact type
schema version
revision
lifecycle status
payload
canonical content hash
parent version
actor and timestamp
provenance
```

Lifecycle status is limited to:

```text
draft → validated → human_review → approved → locked
                        ↘ rejected
approved/locked → deprecated through a new decision, never mutation
```

`stale` is not a lifecycle status in the current design.

## 5. Dependency and impact architecture

Edges express typed dependency:

```text
DERIVED_FROM
REQUIRES
IMPLEMENTS
USES_ASSET
PAYS_OFF
CONTRADICTS
SUPERSEDES
SELECTED_FROM
```

When a new upstream version is approved, M01 performs coarse reachability and creates `impact_record` rows for descendants. It does not attempt semantic path precision.

```yaml
impact_record:
  cause_version_id: ...
  affected_version_id: ...
  classification: possibly_stale
  validator_findings: []
  resolution_status: unresolved
```

A deterministic validator may promote `possibly_stale` to `contradicted`. Human review may mark it `reviewed_valid` or request re-derivation. Path-aware semantic invalidation is deferred until real usage proves it valuable.

## 6. Command and authority boundary

Commands are explicit application use cases:

```text
create_draft
submit_for_validation
request_human_review
approve_version
lock_version
reject_version
create_revision
record_impact_resolution
```

Agent tools expose only proposal-oriented commands:

```text
read_artifact
query_edges
retrieve_evidence
read_skill_resource
propose_artifact
propose_patch
report_finding
```

Approval and locking are never agent tools.

## 7. Agent runtime

Each agent run receives:

- explicit project/run IDs;
- typed input artifact snapshots;
- selected skill refs;
- application policy and budget;
- narrow tools;
- a resolved model alias.

Every run records:

- input version IDs and hashes;
- skill source refs and hashes;
- system/application prompt bundle hash;
- resolved provider/model;
- tool calls;
- retries;
- token/cost data;
- structured output;
- validator findings;
- disposition.

Evidence is serialized as labeled untrusted content and never merged into trusted instructions. Tool enforcement remains the primary security boundary.

## 8. Skill architecture

Release A skill source:

```text
repository path + Git commit + content hash
```

`SKILL.md` follows the portable Agent Skills shape. `skill.yaml` contains only application-specific activation, contracts, permissions, resources, and budgets. `skills.lock` freezes resolution.

A loader validates, hashes, and snapshots skills at process startup or explicit reload. It does not execute bundled scripts.

M12 may add archive upload, quarantine, semver dependency resolution, organization scopes, revocation, and a hosted registry without changing the package format.

## 9. Model routing

Release A uses application configuration:

```yaml
aliases:
  premise_writer:
    provider: configured_provider
    model: configured_model
  continuity_checker:
    provider: configured_provider
    model: configured_model
```

The run stores both alias and resolved model. A gateway service is introduced only when central budgets, routing, failover, or many services justify it.

## 10. Workflow runtime

No durable runtime is required before M04a PASS and M04b completion.

After the story gate, application code targets:

```python
class WorkflowRuntime(Protocol):
    async def start(self, plan, context) -> RunRef: ...
    async def signal(self, run_id, signal) -> None: ...
    async def query(self, run_id) -> RunState: ...
    async def cancel(self, run_id) -> None: ...
```

The M05 ADR compares:

- simple Postgres job/run state;
- DBOS;
- Temporal;
- Restate.

Default hypothesis: DBOS fits the private, low-throughput, Postgres-centered stage. Temporal becomes attractive for independently scaled services, mature operations, and complex multi-tenant orchestration. Postgres remains narrative canon either way.

## 11. Provider architecture

Core contracts contain no provider-specific fields. Compilers create provider bundles:

```text
locked Shot Contract
+ locked Delivery Specification
+ approved asset refs
+ provider capability profile
→ compiled prompt bundle
```

The compiler may translate syntax, add negative constraints, select supported settings, or down-convert delivery requirements. It may not add characters, props, events, emotions, or story facts.

M08 begins with a manual adapter:

```text
export bundle → external provider UI → import output
```

Unknown seed/model/settings remain explicitly unknown.

## 12. Audio architecture

Audio is canonical at project/timeline level, but each shot declares a dialogue source:

```text
canonical_tts
human_recording
native_provider_dialogue
no_on_camera_dialogue
```

Native provider dialogue requires:

1. ASR transcript;
2. comparison with locked dialogue;
3. voice/performance review;
4. explicit human promotion;
5. screenplay revision if words materially differ.

Music cues attach to sequence or scene. Imported/licensed music is default. Generated music is disabled unless project policy and rights allow it.

## 13. Delivery, rights, and provenance

A locked Delivery Specification is available before provider generation. Provider capability checks fail early when a target cannot satisfy mandatory constraints.

Every source and asset has a rights block. Approval requires a populated rights record; release requires cleared rights for intended uses and territories.

Release outputs include:

- human-readable AI-use disclosure;
- machine-readable sidecar provenance manifest;
- hashes for masters and source manifests;
- optional C2PA assertion/signature when configured.

## 14. Timeline architecture

The application owns a richer internal timeline for dialogue takes, music stems, ambience, SFX, automation, and alternatives. It projects editorial structure to OpenTimelineIO. EDL/FCPXML/AAF adapters are export concerns.

Round-trip tests must use the actual target editor rather than only the same library's reader.

## 15. Cost architecture

- `budget_plan` is an approved constraint.
- `cost_ledger` is append-only actual/estimated charge data.
- `cost_projection` is a versioned derived report based on remaining work, observed attempts, and provider price snapshots.

Cost is queryable by stage, artifact, sequence, provider, and approved minute.

## 16. Deployment evolution

### Stage A — private prototype

Next.js, FastAPI, Supabase, repository skills, direct model aliases, and FFmpeg.

### Stage B — private production tool

Add WorkflowRuntime, object storage, media worker, audio providers, manual provider adapter, and delivery pipeline.

### Stage C — production runtime

Add automated provider adapters, full Studio, OTIO/NLE integration, external provenance, and observability.

### Stage D — hosted product

Add hosted skill registry, roles, multi-tenancy, isolation, rate limits, recovery, and operational control plane.

## 17. Architectural fitness tests

CI must continuously prove:

- domain package has no framework/provider imports;
- locked versions cannot mutate;
- agents cannot call approval commands;
- impacts are separate from lifecycle status;
- compilers cannot introduce undeclared entities;
- repository skills resolve to locked hashes;
- untrusted evidence cannot add authority;
- no external provider request occurs in PR CI;
- picture replacement preserves approved soundtrack IDs;
- rights and delivery gates block invalid release;
- manual imports preserve unknown provenance honestly.
