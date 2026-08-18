# M04a protected experiment runbook

**Status:** draft operator guidance. No calibration, pilot, simulation, rating,
freeze, or product decision is claimed by this file.

This runbook is the human/operator sequence for the protected M04a creative
experiment. It is intentionally separate from the deterministic engineering
checkpoint and from the offline Studio demonstration. A blank field, a
placeholder, or an unchecked box is not evidence that a step occurred.

## Authority and scope

Use these documents as the controlling references, in this order:

1. [M04a engineering checkpoint](M04A_ENGINEERING_CHECKPOINT.md) for the
   implementation boundary and known incomplete protected work;
2. [M4 experiment protocol](M4_EXPERIMENT_PROTOCOL.md) for the registered
   hypothesis, sample/rater rules, instrument validity, decision branches, and
   reuse protections;
3. [M04a milestone gate](../prompts/milestones/M04A_STORY_ROOM_GATE.md) for
   the required minimum workflow and exact exit decision;
4. [ADR-005: secrets and ordinary-test egress](adr/ADR-005-SECRETS-AND-EGRESS.md),
   [ADR-006: deterministic fakes and model aliases](adr/ADR-006-FAKES-AND-MODEL-ALIASES.md),
   [ADR-009: typed agent authority](adr/ADR-009-M03-TYPED-AGENT-AUTHORITY.md),
   and [ADR-010: the offline gate boundary](adr/ADR-010-M04A-OFFLINE-GATE-BOUNDARY.md)
   for security, model, authority, and projection boundaries.

The checked-in protocol and examples are templates/fixtures. They are not
evidence that a human calibration or protected run has occurred. Do not edit
the protocol, assignment, anchor, analyzer, simulator, or schema to make a
result easier to obtain.

## Roles and separation of duties

Name roles in the protected run packet before execution. Use role references in
the records; do not put personal contact details or credentials in these
artifacts.

- **Protocol custodian:** owns the draft-to-frozen transition and verifies that
  protocol, prompts, budgets, briefs, assignments, anchors, rule code, and
  simulation assumptions are sealed together.
- **Calibration operator:** runs the non-test calibration brief through all
  three protocol conditions and records raw operational evidence.
- **Pilot coordinator:** recruits at least two non-builder raters, delivers the
  deliberately varied pilot, and records orientation/timing evidence.
- **Sample operator:** generates the frozen primary samples and records every
  technically valid and invalid output. This role cannot select favorites.
- **Rater coordinator:** prepares randomized opaque assignments, confirms
  qualification and conflicts, and collects completed rating records.
- **Analyzer operator:** runs the authoritative analyzer after assignments are
  complete and preserves the raw records and analyzer output.
- **Named reviewer:** inspects the simulate-mode operating-characteristics
  report and records the accepted false-positive, false-negative, and
  measurement-failure trade-offs before primary generation.
- **Decision authority:** records exactly one frozen product decision and its
  permitted next action. This authority is human and cannot be delegated to an
  agent or inferred from a dashboard.

At minimum, the calibration/pilot operator, sample operator, and decision
authority must be independent of the primary sample authorship. The person who
can change prompts, skills, budgets, or selection rules must not inspect
cross-condition primary outputs before the decision. If this separation cannot
be attested, stop and record the gap rather than proceeding.

## Protected packet and status discipline

Create one protected packet outside ordinary development-agent context. Copy
the four draft forms into that packet or complete controlled copies; preserve
the repository templates unchanged. The packet must contain, at minimum:

- the frozen protocol and its content hash;
- calibration and pilot records;
- baseline prompts, Story Room skill lock, budgets, briefs, and reserve
  commitment;
- assignment plan, randomized opaque labels, and positive-control manifest;
- shared rule, analyzer, simulator, and operating-characteristics output;
- sample manifests, target-scene hashes, validation findings, and cost/latency
  evidence;
- completed rater records and technical-abort/replacement records;
- the decision record and any applicable dialogue-spike record.

Use the following state progression:

```text
draft → calibration complete → pilot complete → simulate review complete
      → frozen → primary generation complete → ratings complete
      → analyzed → one decision recorded
```

Only the protocol custodian may mark a packet `frozen`. A frozen packet is
immutable. A technical defect discovered before anyone inspects primary outputs
may require a new protocol version; it must not be silently patched in place.

## Sequential operating procedure

### 0. Confirm the engineering precondition

Read the [engineering checkpoint](M04A_ENGINEERING_CHECKPOINT.md) and verify
that the deterministic code path is available. Confirm that ordinary tests use
fakes/no billable calls, that the rater projection rejects source identifiers,
and that the Studio route is understood as demonstrative only.

Record:

- checkpoint revision/hash: `REPLACE_BEFORE_EXECUTION`
- operator role reference: `REPLACE_BEFORE_EXECUTION`
- unresolved engineering gaps: `REPLACE_BEFORE_EXECUTION`

Do not begin protected generation when the packet still depends on an API,
persistence feature, M04b work, a provider adapter, or an unreviewed schema
change.

The offline compiler can be exercised before a credential exists. Replace the
model and budget placeholders with the intended calibration declarations; the
command emits request descriptors and performs no provider call:

```bash
python scripts/prepare_m4.py \
  --phase calibration \
  --model-alias REPLACE_BEFORE_CALIBRATION \
  --provider REPLACE_BEFORE_CALIBRATION \
  --model REPLACE_BEFORE_CALIBRATION \
  --equal-information-max-calls 1 \
  --equal-information-max-cost-usd REPLACE_BEFORE_CALIBRATION \
  --fixed-budget-conventional-max-calls REPLACE_BEFORE_CALIBRATION \
  --fixed-budget-conventional-max-cost-usd REPLACE_BEFORE_CALIBRATION \
  --story-room-max-calls REPLACE_BEFORE_CALIBRATION \
  --story-room-max-cost-usd REPLACE_BEFORE_CALIBRATION
```

Later, `--mode execute_preflight` checks static controls and the named
credential's presence, but it also makes zero provider calls. A provider-specific
protected adapter remains a separate, explicit step after provider selection.

### 1. Prepare the draft packet

Start with the draft protocol at
`examples/evals/story-room-gate/protocol.yaml`, the assignment/anchor examples,
and the four templates in `templates/`. Copy no reserve contents into the
development-agent context. Confirm:

- protocol status is `draft`;
- draft/null values are enumerated in an operator checklist;
- the calibration brief is non-test and rights-cleared/synthetic;
- primary and reserve brief commitments are held outside prompt/skill author
  context;
- no credential value is written to a record, command log, or prompt;
- the packet has a protected location and access log reference.

If an authorized protected provider call is needed, the operator supplies the
secret at execution through the named environment variable `M04A_PROVIDER_SECRET`.
Never write its value, or a credential-value field, into a record, command log,
prompt, or rater packet.

### 2. Run the non-test calibration brief

Use the calibration form at
[`M04A_CALIBRATION_RECORD.template.yaml`](../templates/M04A_CALIBRATION_RECORD.template.yaml).
Run the same calibration brief through equal-information, fixed-budget
conventional, and Story Room conditions with the declared model-family access
and input material. The calibration is for budget, timing, quality-range, and
operational assumptions; it is not part of the 27 primary samples and cannot
be used to tune a primary output after the fact.

Record raw evidence, not conclusions:

- input/brief reference and rights/provenance references;
- prompt, skill, code, and configuration references with hashes when available;
- output references and technical validity findings for all conditions;
- elapsed time, provider usage/cost evidence, retries, and failure causes;
- the projected Story Room cap per sample and the fixed conventional cap using
  the predeclared multiplier;
- unresolved metadata or assumptions that must be carried into sensitivity
  analysis.

Do not call the calibration a product result, do not select a preferred branch,
and do not reveal any protected reserve material.

### 3. Run the two-rater instrument/timing pilot

Use [`M04A_RATER_PILOT_RECORD.template.yaml`](../templates/M04A_RATER_PILOT_RECORD.template.yaml).
The pilot requires at least two non-builder raters and deliberately varied
quality examples. Before they rate, provide the frozen dimension guide and
record qualification/conflict checks. Each pilot rater must explain the three
primary dimensions in their own words and identify the intended direction for
each. If either rater misses a target direction, stop, revise the guide or
instrument, and repeat the pilot before freeze.

Measure:

- completion time with the forced-choice controls included;
- ambiguities, missing content, accessibility/technical failures, and
  replacement needs;
- scored-item tie behavior as a diagnostic only;
- forced-choice instrument direction accuracy;
- likely rater and brief heterogeneity;
- whether the workload fits the declared 45-minute target.

Do not pool pilot responses with primary ratings. A pilot rater must not see
primary condition outputs, the sealed condition-to-label map, or control truth.

### 4. Resolve calibration and pilot inputs before freeze

The protocol custodian reviews the calibration and pilot forms with the named
reviewer. Resolve every `REPLACE_BEFORE_FREEZE` and `null` required for freeze:

- protocol version and source hashes;
- baseline prompt references and skill lock;
- calibration-informed Story Room cap and fixed conventional cap;
- explicit per-condition call/cost budgets, with the conventional cap fixed at
  exactly `1.5 ×` the Story Room cap;
- three primary brief hashes and the external reserve commitment;
- target middle-scene position and page range;
- assignment mode, three judgments per scored triplet, and workload limits;
- randomized opaque-label procedure and sealed condition map;
- positive-control manifest and forced-choice/technical-abort rules;
- analyzer/simulator/shared-rule source hashes;
- dialogue-spike applicability decision.

Do not replace an unknown with a plausible value. If a required artifact is
not available, the packet remains draft and execution stops.

### 5. Run and review operating characteristics in simulate mode

After calibration assumptions are recorded, run the authoritative simulator in
the required mode. The command shape is illustrative; substitute only frozen
paths and capture the command/output reference in the protected packet:

```bash
python scripts/simulate_m4.py \
  --protocol examples/evals/story-room-gate/protocol.yaml \
  --assignment-plan examples/evals/story-room-gate/assignment-plan.example.yaml \
  --run-mode standard_six \
  --trials 4000 \
  --true-preferences 0.55 0.65 0.75 \
  --reliability-mode simulate \
  --output <protected-operating-characteristics-output>
```

The simulator must exercise central and lower/higher heterogeneity sensitivity
scenarios, forced-choice anchor accuracy, PASS/MIXED/FAIL/INCONCLUSIVE
branches, the five-run MIXED repeat, and eventual-PASS behavior. A
non-degenerate `INCONCLUSIVE` branch must arise under at least one plausible
scenario. `assume_interpretable` is a secondary diagnostic only and cannot
satisfy freeze.

Complete [`M04A_OPERATING_CHARACTERISTICS_REVIEW.template.md`](../templates/M04A_OPERATING_CHARACTERISTICS_REVIEW.template.md)
with the output reference, assumptions, tables, and named human review. The
reviewer must explain why the false-positive, false-negative, and instrument
failure trade-offs are acceptable for this exploratory product decision. A
review signature or equivalent attestation is required before freeze; a blank
review field is not approval.

### 6. Freeze the protocol and packet

The protocol custodian performs a read-only diff and verifies that all freeze
inputs are present and hash-pinned. Freeze occurs before final primary
generation. At freeze:

- set the protocol status and freeze metadata in the protected copy;
- preserve the repository draft as a template unless a separately authorized
  change is made;
- seal prompts, skills, budgets, briefs, reserve commitment, assignments,
  target-scene rule, labels, anchors, rules, analyzer, simulator, and
  simulation assumptions;
- record the packet manifest/hash and named review;
- attest that no primary output was inspected across conditions before the
  freeze decision.

After freeze, a prompt, skill, model, budget, assignment, label rule, anchor,
or threshold change requires a new protocol version. Do not continue an old
packet under a new assumption.

### 7. Generate all primary samples without builder selection

Generate the declared primary design: three primary briefs × three independent
runs × three conditions = 27 samples. Each technically valid sample is kept
and rated. The builder/operator may not inspect outputs and select favorites,
replace weak samples, cherry-pick a scene, or suppress a technically valid
output. Technical invalidity is allowed only for a predeclared reason such as
schema failure, missing required scene, provider outage before completion, or
budget-cap breach.

For every output, preserve:

- condition/run/brief truth in the sealed admin manifest only;
- opaque sample token and content hash for the rating projection;
- all three scenes and the position-based middle-scene reference;
- validator findings, validity disposition, cost, latency, retries, and honest
  unknown metadata;
- the neutral context card and rights/provenance references.

The rater packet must never contain the condition map, source sample IDs,
brief/run identifiers, positive-control truth, or expected responses.

### 8. Prepare and attest blinded assignments

Use a supported assignment mode from the frozen protocol. Every scored triplet
must receive exactly three judgments. Every primary rater completes every
assigned forced-choice instrument task. If timing requires a change, use only a
predeclared supported mode (for example, the seventh-rater or degraded-diversity
mode); never reduce replication informally.

Before a rater sees a task, the rater coordinator verifies:

- qualification, language ability, independence, and conflicts;
- randomized opaque labels and a sealed condition map;
- identical neutral context and matched-scene display;
- forced-choice controls with no substantive tie response;
- a separate report-technical-problem action that aborts/replaces the task
  before dataset freeze rather than scoring it;
- access logs showing that no rater or creative-change authority received
  control truth or unblinding information.

### 9. Collect ratings and technical-abort records

Collect the raw rating records without editing responses. Preserve elapsed time,
missingness, comments, task completion, and any technical abort/replacement
record. A technical problem is not a tie or a preference. Do not ask a rater to
guess when content is missing or unreadable.

The analyzer must evaluate forced-choice instrument validity before exposing
scored preferences. If the instrument fails, the decision is `INCONCLUSIVE` and
scored preference values remain withheld. Raw agreement, nominal Krippendorff
alpha, and scored-item tie rate are diagnostics, not independent gates.

### 10. Analyze and record exactly one decision

Run the authoritative analyzer using the frozen packet and the shared pure rule
module. Verify that:

- all required assignments are present;
- technically valid outputs are included;
- the positive-control thresholds pass before preference results are read;
- aggregate thresholds are checked against both baselines;
- per-brief robustness uses only the stronger aggregate baseline;
- continuity non-inferiority and evidence-strength labels are reported;
- secondary dimensions and reliability diagnostics cannot rescue or reject the
  primary gate by themselves;
- costs, workload, latency, invalid outputs, and dialogue evidence are carried
  into the report.

Complete the repository's
[decision template](../examples/evals/story-room-gate/decision-template.md)
from analyzer output and human review. Record one and only one of `PASS`,
`MIXED`, `FAIL`, or `INCONCLUSIVE`. A draft form, example output, or static UI
fixture is not a decision.

### 11. Apply the branch and stop at the gate

- **PASS:** only after the frozen protocol and instrument pass; the recorded
  next action may authorize M04b. Do not begin M04b in this runbook.
- **MIXED:** permit exactly one bounded skill/contract change and one fresh
  five-run-per-condition reserve-brief repeat. Do not pool round one and the
  repeat. The repeat has its own raw records and decision review.
- **FAIL:** stop platform expansion and reassess/reposition the thesis.
- **INCONCLUSIVE:** repair the measurement protocol; do not tune creative
  skills from withheld preferences.

For an `INCONCLUSIVE` rerun, re-use frozen primary samples only if every
protocol attestation is true: scored results were withheld by code, the
unblinding map was never opened, no creative-change authority inspected
cross-condition outputs, the creative pipeline is unchanged, and a fresh rater
pool with newly randomized labels is available. If any attestation is false or
unknown, use fresh primary briefs and samples under a new protocol version.

### 12. Run the dialogue-feasibility spike when applicable

If the first film requires visible speech, run the separate 5–15 second manual
speaking-character spike described in [the protocol's dialogue-feasibility
section](M4_EXPERIMENT_PROTOCOL.md#12-parallel-speaking-character-feasibility-spike).
Record attempts to first acceptable take, rejection categories, latency/cost
evidence, rights note, transcript where applicable, and a bounded production
consequence. This is protected human evidence, not a provider adapter or M04b
implementation. If visible dialogue is not required, record
`not_applicable_no_visible_dialogue` with a role attestation.

## Stop conditions

Stop the packet and escalate to the protocol custodian when:

- a required source/hash/brief/budget/assignment field is unknown at freeze;
- a protected person cannot attest to independence or access separation;
- reserve contents, condition truth, anchor truth, or unblinding data leaked;
- a technical defect is being proposed as a tie or as a silently replaced
  preference;
- a builder wants to select, suppress, or rewrite a technically valid sample;
- the simulator was run in a non-freeze mode or lacks sensitivity/measurement
  failure behavior;
- a schema or decision-rule change appears necessary;
- a credential value, personal data, or secret is about to enter an artifact;
- anyone proposes starting M04b before a recorded `PASS`.

## Handoff checklist

The protected packet is ready for human gate review only when every item below
has an evidence reference or an explicit attestation:

- [ ] calibration form complete and non-test evidence separated from conclusions;
- [ ] two-rater pilot complete, varied quality confirmed, and guide decision recorded;
- [ ] all freeze placeholders resolved or an explicit draft blocker recorded;
- [ ] simulate-mode operating characteristics reviewed and signed by a named human;
- [ ] protocol and all dependencies frozen before primary generation;
- [ ] 27 primary samples generated with no builder selection;
- [ ] assignments provide three ratings per scored triplet;
- [ ] forced-choice instrument and technical-abort records complete;
- [ ] analyzer output and non-gating diagnostics preserved;
- [ ] exactly one decision recorded with permitted/prohibited next actions;
- [ ] INCONCLUSIVE reuse attestations or fresh-sample plan recorded when applicable;
- [ ] dialogue-spike record complete or applicability marked;
- [ ] no credential values, reserve contents, or unblinding identifiers are in the rater packet.

Until this checklist is complete and the decision is human-recorded, M04a
remains open and M04b remains prohibited.
