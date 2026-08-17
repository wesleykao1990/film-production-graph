# Product Requirements Document — Final v3.0.0

## Product

**Working name:** Film Production Graph  
**Status:** Final reviewed implementation handoff  
**Initial mode:** Private, solo-builder production tool assisted by coding agents  
**First outcome:** A reproducible 60–180 second microfilm  
**Productization rule:** Multi-user platform work begins only after story-quality and production-feasibility gates pass

---

## 1. Vision

Create an AI-assisted film studio that makes the filmmaker's evidence, choices, constraints, rejected alternatives, character state, audio identity, delivery requirements, rights, and editing decisions more durable than any generation model.

The system is not a one-prompt movie generator. It is a typed Narrative and Film Production Graph in which agents propose, software validates, humans approve, and provider prompts are compiled downstream.

## 2. Problem

Current AI-film workflows commonly fail because they:

- begin with generic prompts rather than specific evidence and authorial constraints;
- allow each model call to invent facts independently;
- store continuity in prompt text or model memory;
- regenerate large sections when a local element fails;
- couple projects to proprietary provider canvases;
- hide rejected alternatives and human rationale;
- allow picture regeneration to replace voice, ambience, or music;
- generate BGM shot-by-shot;
- discover delivery, rights, subtitle, or provenance requirements only at export;
- build infrastructure before proving that the writing workflow creates better work.

## 3. Product principles

1. Story quality is tested before video investment.
2. Postgres typed artifacts are canon.
3. Agents propose; humans or explicit policy approve.
4. Locked versions are immutable.
5. Impact is recorded separately from lifecycle state.
6. Prompts compile approved facts; they cannot create new ones.
7. Audio identity is persistent and independently editable.
8. Provider-native audio is a candidate, not automatically truth.
9. Rights and delivery are canonical constraints.
10. Skills are versioned and least-privilege.
11. Provider changes must not require rewriting project canon.
12. Evaluation dimensions remain separate.

## 4. Initial assumptions

```yaml
builder: solo_with_coding_agents
users_in_release_a: 1
hosting_in_release_a: local_or_private_hosted
first_film_duration_seconds: 60_to_180
first_film_languages: configured_per_project
recurring_characters: 2_to_3
principal_locations: 1_to_2
preferred_first_provider_path: manual_export_import
```

## 5. Goals

### G1 — Prove better writing

Use a pre-registered internal decision protocol to determine whether the structured Story Room improves specificity, character voice, and causal dramatic progression over fair baselines.

### G2 — Human-controlled canon

Agents may create proposals and patches but cannot approve, lock, or silently overwrite canon.

### G3 — Explicit state

Represent story, character knowledge, relationships, audience state, sequence state, locations, props, costumes, voice, music, ambience, rights, costs, and delivery requirements explicitly.

### G4 — Complete lineage

Trace final visual and audible ranges to source evidence, story decisions, skills, contracts, provider runs, human selections, and edits.

### G5 — Extensible methods

Allow custom instruction and declarative workflow skills without application-code changes. Release A uses repository packages; hosted installation is deferred.

### G6 — Provider independence

Language, image, video, voice, music, SFX, lip-sync, ASR, and cleanup providers sit behind stable interfaces.

### G7 — Finish one film cheaply

Use screenplay, storyboard, temporary audio, animatic, one dialogue feasibility spike, and manual provider import before broad API integration.

### G8 — Provide an executable behavioral reference

Ship a local deterministic prototype that demonstrates versioned canon, lineage, impact records, repository skills, typed proposals, and separate human approval without being mistaken for the production architecture.

## 6. Non-goals before validation

- Fully autonomous feature-film generation.
- Public multi-tenant hosting.
- Hosted skill marketplace or arbitrary skill uploads.
- Arbitrary runtime code execution.
- Full React Flow production studio before the domain stabilizes.
- A custom NLE or DAW.
- Many provider APIs before one manual production path works.
- Model training, Neo4j, GraphRAG, Kubernetes, or a free-form swarm.
- Automatic legal clearance.

### Reference prototype boundary

The package includes `prototype/`, a FastAPI/SQLite/static-UI reference application. It is required to stay runnable and tested, but it is not production milestone completion. Production persistence remains Supabase Postgres; production agents remain PydanticAI behind application-owned tools; production authentication, RLS, media processing, and durable execution arrive only in their named milestones.

## 7. Core concepts

### Artifact and version

A typed domain object with immutable versions, schema version, state, content hash, actor, provenance, and dependencies.

### Canon

Approved or locked artifact versions that define what the project currently treats as true.

### Impact record

A separate record created when an upstream dependency changes. Classifications:

```text
possibly_stale
contradicted
reviewed_valid
rederive_requested
resolved
```

### Sequence

A dramatic/production unit spanning one or more scenes. Music cues, visual strategies, location transitions, and delivery chunks may attach to it.

### Delivery Specification

Locked project requirements such as aspect ratio, resolution, frame rate, loudness, duration, subtitle languages, and required masters.

### Rights record

The holder, permitted uses, territory, duration, source evidence, provider terms, likeness/voice consent, and release status for an asset or source.

### Subtitle track

A derived but versioned track linked to canonical dialogue and timeline timing, exportable as SRT/VTT or burn-in.

### Cost records

- `budget_plan`: approved limits and allocation.
- `cost_ledger`: immutable actual charges and estimates attached to runs/assets.
- `cost_projection`: versioned derived estimate for remaining work.

### Skill

A portable `SKILL.md` plus app-specific permissions/contracts in `skill.yaml`. Release A pins repository paths by Git source and content hash.

### Workflow plan

A validated declarative plan interpreted by a runtime only after M4. The runtime is replaceable behind `WorkflowRuntime`.

### Generation attempt

A provider or manual run with prompt bundle, input assets, settings, resolved model/provider, output, cost, rights/provider policy, findings, and disposition.

## 8. Primary journeys

### J1 — Prove the Story Room

1. Lock a Creative Constitution and Evidence Bank.
2. Run equal-information and pre-frozen fixed-budget baselines.
3. Generate independent premise candidates.
4. Approve character, relationship, beat, sequence, and Scene Contract artifacts.
5. Generate screenplay patches through repository skills.
6. Run blinded evaluation through the frozen M4 protocol.
7. Verify rater reliability before interpreting preference.
8. Record PASS, MIXED, FAIL, or INCONCLUSIVE.
9. Complete the deferred Story Room passes only after PASS.

### J2 — Add a custom skill

1. Add a skill directory by pull request.
2. Validate Agent Skills frontmatter and `skill.yaml`.
3. Run trigger, non-trigger, contract, permission, and injection tests.
4. Record the source commit and content hash in `skills.lock`.
5. Bind the skill to an agent/workflow.
6. Record the resolved skill in each run.

### J3 — Build an audio-consistent scene

1. Approve persistent Voice Profiles.
2. Select a per-shot dialogue mode: canonical TTS, human recording, provider-native, or no on-camera dialogue.
3. Attach music to a sequence/scene cue.
4. Maintain continuous location ambience.
5. Place Foley/SFX on a timeline.
6. Replace picture without silently changing approved audio.

### J4 — Produce one film manually

1. Approve Shot Contracts and storyboard.
2. Build an audio animatic.
3. Complete a short talking-character/lip-sync feasibility test when needed.
4. Export prompt bundles and references to a provider.
5. Import outputs with honest unknown metadata.
6. Select takes, assemble in FFmpeg/Resolve, generate subtitles, validate delivery, and export provenance.

### J5 — Productize later

After both gates pass, add durable workflows, full lineage UI, production adapters, hosted registry, roles, multi-tenancy, and recovery.

## 9. Functional requirements

### FR-0 Executable reference prototype

- Run locally without credentials or provider accounts.
- Seed the deterministic Blue Pen project.
- Demonstrate immutable payload versions, human approval/locking, lineage, impact records, whole-directory skill hashing, and a workflow paused at human approval.
- Make zero live model or media-provider calls.
- Clearly label SQLite, static UI, and mock execution as non-production.
- Keep its tests passing throughout implementation so it remains an executable behavioral specification.

### FR-1 Projects and policy

- Create/archive/duplicate projects.
- Store owner, delivery specification, budgets, default rights policy, model aliases, skill lock, language, and provider policy.
- Release A may use a single owner; schema must not prevent later membership.

### FR-2 Artifact versions and lineage

- Immutable versions with optimistic concurrency.
- Valid lifecycle transitions: `draft`, `validated`, `human_review`, `approved`, `locked`, `rejected`, `deprecated`.
- Dependency edges and bidirectional lineage.
- Coarse graph reachability impacts in v1.
- Bulk acknowledge, revalidate, and rederive actions.
- Actual contradictions are distinguished from possible impacts.

### FR-3 Story Room

- Creative Constitution and Evidence Bank.
- Independent premise branches.
- Human comparison/combination rationale.
- Characters, relationships, audience state, beats, sequences, setups/payoffs, Scene Contracts, screenplay scenes, and patches.
- Behavior, dialogue, subtext, compression, filmability, continuity, and voice passes.
- Deterministic hard validators plus separate interpretive diagnostics.
- Fountain export.
- Minimal review UI sufficient for approvals and blind comparison.

### FR-4 Repository skill system

- Discover approved skill folders in configured repository roots.
- Validate portable `SKILL.md` fields.
- Validate app-specific permissions, contracts, budgets, activation, and resources in `skill.yaml`.
- Run trigger and adjacent non-trigger tests.
- Generate `skills.lock` entries with source ref and content hash.
- Prohibit arbitrary executable content.
- Record exact skill resolution in provenance.
- Defer archive upload, semver registry, organization sharing, revocation service, and marketplace UI to M12.

### FR-5 Agent runtime and security

- Typed inputs/outputs.
- Narrow application tools.
- Agent/skill-derived permissions and budgets.
- Fake models in ordinary CI.
- Direct application model aliases before a gateway service is justified.
- Untrusted evidence delimiters and source labeling.
- Security corpus proving untrusted text cannot elevate authority.
- No self-approval.

### FR-6 Story-quality gate

- Calibrate on non-test material, then freeze baseline prompts, fixed budgets, three primary briefs, reserve-brief commitment, target-scene rule, scored and forced-choice anchor assignments, rater criteria, positive-control thresholds, operating-characteristic assumptions, analysis code, and decision branches before final generation.
- Preserve every output, anchor, assignment, rating, exclusion, and decision.
- Gate only on the three primary dimensions, hard-continuity non-inferiority, and a blinded positive-control instrument check; sample secondaries for diagnosis.
- Report raw agreement and nominal Krippendorff alpha as non-gating diagnostics because skewed marginals can make chance-corrected agreement behave perversely.
- Treat positive-control or protocol failure as INCONCLUSIVE rather than creative FAIL, and withhold preference results from skill tuning.
- Use five fresh runs per condition on the sealed reserve brief for the one bounded MIXED repeat; budget the expected repeat rather than treating it as remote contingency.
- Do not proceed to M04b or broad production integration after FAIL or INCONCLUSIVE.

### FR-7 Workflow runtime after gate

- Application-owned `WorkflowRuntime` interface.
- ADR comparison of simple jobs, DBOS, Temporal, and Restate.
- Durable approvals, retries, cancellation, resumability, idempotency, bounded loops, and small serialized state.
- Postgres remains narrative/domain canon regardless of runtime.

### FR-8 Audio, subtitles, and delivery

- Persistent Voice Profiles and per-line performances.
- Canonical dialogue WAVs or human recordings.
- Provider-native dialogue candidate path with ASR comparison to locked lines and explicit promotion.
- Music Bible, motifs, sequence/scene cues, stems, and forbidden defaults.
- Imported/licensed music default; generation behind a feature flag.
- Location acoustics, ambience, Foley, and SFX.
- Subtitle tracks and SRT/VTT/burn-in export.
- Locked Delivery Specification and media validation.

### FR-9 Previsualization

- Shot Contracts with story function, information delta, visible action, continuity, screen direction, duration, and audio policy.
- Storyboards and audio animatic.
- Comprehension, pacing, visual necessity, and continuity review.
- One manual 5–15 second speaking-character spike in parallel with M04a when visible dialogue is required, followed by a productionized repeat in M07.

### FR-10 Provider operations

- Manual export/import adapter first.
- Stable interfaces for LLM, image, video, TTS, music, SFX, ASR, lip-sync, and cleanup.
- Capability matrix and provider policy records.
- Provider prompt compilers outside core contracts.
- Honest unknown metadata.
- Budgets, idempotency, callbacks, cancellation, and cost records for automated adapters.

### FR-11 Editing and release

- Internal non-destructive timeline plus OTIO editorial projection.
- Rough/fine cuts and selected/rejected status.
- Picture replacement without unintended soundtrack mutation.
- Export master/proxy/stems/Fountain/OTIO/SRT/VTT/sidecar provenance.
- Optional C2PA credential when configured.
- Human-readable AI-use disclosure.
- Rights and delivery validation block release.

### FR-12 Full Studio and hosted registry

- Full lineage graph, impact visualization, workflow monitor, generation comparison, audio/timeline views, skill upgrade review, multi-user roles, and hosted skill package lifecycle only after validation.

## 10. Non-functional requirements

- Clean clone bootstraps and tests without provider credentials.
- Database-level project isolation when multi-user hosting is introduced.
- No runtime execution of uploaded skill code.
- No accidental external requests in PR CI.
- Complete run/asset provenance and immutable actual cost records.
- Project exports remain provider-independent.
- UI approval/evaluation paths are keyboard accessible.
- Large graph views use filtering/progressive loading rather than rendering everything.

## 11. M4 decision rule

M04a is a product decision heuristic, not a statistical-significance claim. Before it can freeze, the project must run the exact proposed rule through `scripts/simulate_m4.py`, using calibration-informed central and sensitivity assumptions. A named human must review the simulated PASS/MIXED/FAIL/INCONCLUSIVE behavior, positive-control pass probability, and five-run repeat behavior at several true-preference levels and commit the report, assumptions, protocol hash, anchor hash, and shared rule-code hash.

In every evidence-strength mode, the Story Room passes only when:

- aggregate specificity preference is at least 60% against both baselines;
- aggregate character-voice preference is at least 60% against both baselines;
- aggregate causal-progression preference is at least 55% against both baselines;
- for each primary dimension, Story Room receives a strict majority against the stronger aggregate baseline on at least two of three briefs;
- hard continuity violations are no worse than the best baseline;
- the blinded forced-choice positive-control anchors pass for all three primary dimensions and in aggregate; technical anchor defects are aborted and replaced before dataset freeze, never recorded as ties.

The aggregate comparison carries the effect-magnitude requirement. The per-brief comparison is only a cross-brief direction check and therefore does not repeat the full threshold against both baselines on every brief. Raw agreement, nominal Krippendorff alpha, and tie rate are reported as non-gating diagnostics because skewed marginals can make chance-corrected agreement collapse even under uniform preference.

Standard assignments use three ratings per triplet with six raters by default, five raters as a frozen recruitment fallback, or seven raters as a frozen timing fallback. If the timing pilot fails, the project recruits the seventh rater or shortens the rated scene within the predeclared range; it must not reduce ratings per triplet.

The three-rater degraded mode assigns all three raters all nine triplets, uses the same numerical thresholds, and is labeled weaker evidence because rater diversity is lower. Secondary dimensions do not gate.

MIXED permits one bounded change and one hash-committed reserve-brief repeat using five fresh runs per condition. The repeat uses the same primary thresholds, has no extra per-brief requirement, and reports round one separately rather than pooling pre-revision and post-revision data. Expected cost planning includes `P(MIXED) × 15` repeat samples and a second rating batch. FAIL stops expansion. INCONCLUSIVE requires a new measurement protocol and a fresh rater pool. Frozen primary samples may be re-rated only when preference results were withheld, the unblinding map remained sealed, no cross-condition inspection occurred under creative authority, and the creative pipeline is unchanged; otherwise fresh briefs and samples are mandatory. M04b begins only after PASS.

## 12. MVP acceptance film

`blue-pen-film` is accepted when a user can:

1. record an M04a PASS and complete M04b;
2. lock story, sequence, Scene Contract, Shot Contract, Delivery Specification, and rights artifacts;
3. maintain two persistent voices and one sequence music cue;
4. use canonical or approved native dialogue according to explicit shot policy;
5. create subtitles and continuous ambience;
6. export/import at least two real picture takes manually;
7. replace picture without silently changing approved audio;
8. assemble a 60–180 second film;
9. export master, subtitles, human disclosure, and provenance sidecar;
10. trace every selected range backward.

## 13. Release strategy

### Release A — Does it write better?

M00–M04a. Hard gate: the executable Story Room decision protocol. M04b is conditional on PASS.

### Release B — Can it become a film?

M05–M08. Gate: a restart-safe, audio-consistent, delivery-valid finished microfilm using manual provider import.

### Release C — Can production scale?

M09–M10. Gate: provider-neutral automated production, full Studio, editorial round trip, and external provenance.

### Release D — Can it become a hosted product?

M11–M12. Gate: regression, isolation, registry, recovery, security, and staging validation.

## 14. Open project-specific decisions

Resolve during the M04a manual spike and before M06/M07:

- actual first-film language(s);
- whether faces speak on camera;
- target editor and delivery platform/festival;
- first voice/TTS or human-recording path;
- first lip-sync/native-dialogue provider path;
- imported music source and license;
- required subtitle languages;
- distribution territories and intended commercial uses.
