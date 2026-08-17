# Domain and Data Model — Final reviewed specification

## 1. Modeling principles

- Identity and version are separate.
- Locked versions are immutable.
- Lifecycle status and upstream-change impact are separate.
- Domain truth is typed and queryable; vectors are retrieval aids only.
- Every asset has rights, provenance, and content hashes.
- Actual costs are append-only; projections are derived.
- Provider/runtime-specific payloads are not core domain fields.

## 2. Core relational model

### Projects

```text
projects
project_settings
project_model_aliases
project_provider_policies
project_skill_locks
project_memberships          # optional until hosted mode
```

### Artifacts

```text
artifact_identities
  id, project_id, artifact_type, logical_key

artifact_versions
  id, artifact_id, schema_version, revision, lifecycle_status,
  payload_json, content_hash, parent_version_id, actor, created_at

artifact_edges
  from_version_id, to_version_id, edge_type, metadata

impact_records
  cause_version_id, affected_version_id, classification,
  validator_findings, resolution_status, resolution_actor, resolved_at
```

Lifecycle:

```text
draft
validated
human_review
approved
locked
rejected
deprecated
```

Impact classifications:

```text
possibly_stale
contradicted
reviewed_valid
rederive_requested
resolved
```

### Decisions and approvals

```text
approvals
human_decisions
candidate_combinations
review_comments
```

A human decision may select, reject, combine, reopen, acknowledge impact, or request re-derivation. Combination records identify exact source components.

### Runs and provenance

```text
run_records
run_inputs
run_skills
run_tools
run_outputs
validator_findings
prompt_bundles
```

Every run stores alias and resolved model/provider, code version, skill hash, schema versions, retries, cost, and disposition.

### Assets and rights

```text
assets
asset_versions
rights_records
consent_records
provider_policy_snapshots
```

`rights_records` include:

```text
rights_status
holder
source_type
permitted_uses
territories
start/end dates
attribution
license evidence assets
voice/likeness consent refs
provider terms snapshot
reviewed_by/reviewed_at
```

Suggested status:

```text
unverified
declared
cleared
restricted
expired
rejected
```

An asset cannot reach `approved` without at least a populated/declaration record. It cannot enter a release unless status is `cleared` for the intended use and territory.

### Cost

```text
budget_plans
cost_ledger_entries
cost_projections
provider_price_snapshots
```

Ledger entries are immutable. Projections reference a price snapshot and observed attempt rates.

### Provider operations

```text
provider_jobs
provider_callbacks
manual_provider_tasks
generation_attempts
asset_selects
```

Manual imports use null/unknown values rather than guessed provider metadata.

### Timeline and release

```text
internal_timelines
timeline_versions
timeline_tracks
timeline_items
subtitle_tracks
subtitle_cues
edit_decisions
release_versions
release_assets
provenance_manifests
```

OpenTimelineIO is an editorial projection/export, not the only internal audio representation.

## 3. Required artifact types

### Story and authorship

```text
creative_constitution
evidence_item
premise_candidate
character
relationship
audience_state
beat
sequence
setup_payoff
scene_contract
screenplay_scene
screenplay_patch
critic_finding
human_decision
```

### Production

```text
visual_bible
location_state
prop_state
costume_state
shot_contract
storyboard_panel
compiled_prompt
generation_attempt
asset_select
```

### Audio

```text
voice_profile
voice_performance
dialogue_asset
pronunciation_dictionary
music_bible
music_cue
music_stem
ambience_profile
foley_cue
sfx_cue
audio_timeline
```

### Delivery/governance

```text
delivery_spec
subtitle_track
rights_record
provider_policy
budget_plan
cost_ledger
cost_projection
impact_record
provenance_manifest
ai_disclosure
release_manifest
```

## 4. Selected payloads

### Sequence

```yaml
sequence_id: SEQ_03
title: Audit Discovery
scene_ids: [S07, S08, S09]
dramatic_function: Mara moves from concealment to active complicity.
start_state_ref: ...
end_state_ref: ...
music_cue_refs: [M03]
visual_strategy: Progressively remove stable frontal compositions.
```

### Delivery Specification

```yaml
delivery_spec_id: DELIVERY_V1
aspect_ratio: "2.39:1"
width: 3840
height: 1608
frame_rate: "24/1"
audio_sample_rate_hz: 48000
audio_channels: stereo
loudness_target_lufs: -14
true_peak_max_dbtp: -1
maximum_duration_seconds: 180
subtitle_languages: [en, ja]
required_exports:
  - review_h264
  - master_prores
  - srt
  - vtt
  - provenance_sidecar
```

### Impact record

```yaml
cause_version_id: UUID
affected_version_id: UUID
classification: possibly_stale
reason: Upstream constitution received a new locked version.
validator_findings: []
resolution_status: unresolved
```

### Subtitle track

```yaml
language: en
source_dialogue_version_ids: [...]
timeline_version_id: ...
cues:
  - start_ms: 1200
    end_ms: 3100
    text: You already knew.
    speaker_ref: MARA
review_status: approved
```

### Cost projection

```yaml
price_snapshot_at: 2026-08-17T00:00:00Z
remaining_shots: 12
observed_attempts_per_selected_shot: 3.2
projected_by_stage:
  video_generation_usd: 84.00
  audio_usd: 8.00
  post_processing_usd: 2.00
assumptions: [...]
```

## 5. Serialization and hashing

Canonical hashing must define:

- UTF-8;
- normalized Unicode;
- sorted object keys;
- stable number representation;
- no transient timestamps or database IDs inside payload hash unless semantically required;
- normalized line endings;
- content hashes for referenced assets.

Run provenance may hash the artifact snapshot plus selected skills, prompt bundle, and provider settings separately.

## 6. Optimistic concurrency

Every mutation command includes expected current revision. Conflicts return both versions and require explicit merge/retry. Agent proposals never overwrite a newer human edit.

## 7. Impact propagation v1

On approval/lock of a new parent version:

1. traverse directed dependency edges;
2. create idempotent impact rows for reachable descendants;
3. run cheap validators for known contradictions;
4. do not mutate descendant lifecycle status;
5. expose bulk actions.

Path-aware payload dependency tracking is deferred.

## 8. RLS and private mode

Release A may run as one private user, but tables still carry `project_id`. Hosted mode later adds membership-based RLS. Service-role credentials never reach the browser.
