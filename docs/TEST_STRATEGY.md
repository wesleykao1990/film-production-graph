# Test and Evaluation Strategy — Final reviewed specification


## Reference prototype regression suite

The final package includes a deterministic FastAPI/SQLite prototype. Its tests run before production milestone tests and cover immutable versioning, separate approval/locking, graph-reachability impact records, whole-directory skill hashing, workflow pause at human approval, untrusted-text authority separation, reset behavior, and the static/API smoke path. Passing this suite does not count as M00 or later milestone completion; it protects the behavioral contract while production code evolves.

## 1. Principle

Deterministic software guarantees belong in ordinary CI. Probabilistic model quality and real provider behavior belong in protected/manual evaluation. Creative dimensions remain separate.

## 2. Pull-request test layers

### Unit/property

- canonical serialization/hashing;
- lifecycle transitions;
- impact creation/resolution;
- permission intersection;
- skill parsing and whole-package locking;
- prompt compilation fact constraints;
- subtitle timing;
- delivery/media validation;
- cost aggregation.

### Contract

- JSON Schemas;
- agent tool/output contracts;
- skill manifest/resources;
- workflow runtime adapter;
- provider adapter;
- OTIO projection.

### Integration

- migrations;
- artifact/approval/impact flow;
- rights gate;
- fake model run;
- manual import;
- FFmpeg fixture;
- minimal UI review flow.

### Security

- prompt-injection/authority corpus from M03;
- project isolation;
- skill path/symlink/executable rejection;
- egress guard;
- secret redaction;
- provider callback tests when introduced.

## 3. Protected/manual tests

- M04a real-model decision protocol;
- human blind ratings;
- multi-run variance;
- manual M04a and productionized M07 dialogue feasibility;
- real provider sandbox;
- `blue-pen-film` production;
- target NLE round trip;
- optional C2PA signing;
- cost/latency comparison.

## 4. Core invariants

1. Locked versions cannot mutate.
2. Agents cannot approve or lock.
3. Impact state is separate from lifecycle.
4. Untrusted content cannot elevate authority.
5. Prompt compiler cannot introduce facts.
6. Repository whole-skill-directory hash must match lock, including references, schemas, and tests.
7. Picture replacement preserves approved soundtrack refs.
8. Native dialogue cannot rewrite screenplay silently.
9. Music has sequence/scene scope.
10. Rights and delivery block invalid release.
11. Manual import does not fabricate metadata.
12. Final ranges have lineage.

## 5. Golden assets

### `blue-pen-fixture`

- fake models/providers;
- frozen media bytes;
- deterministic IDs/hashes;
- every PR;
- includes both canonical and native-dialogue test cases using fake ASR.

### `blue-pen-film`

- real generations and human selections;
- manual/nightly;
- no byte stability;
- actual rights/provider policy and delivery records.

### Story Room gate

One calibration brief, three frozen primary briefs, an externally held reserve commitment, baselines, rater guide, scored and anchor assignments, rating schemas, positive-control instrument check, non-gating agreement diagnostics, and decision logic.

## 6. M04a gate tests

- non-test calibration completes before freeze;
- protocol/baseline/budget/brief/assignment/anchor/rule/analyzer/simulator hashes freeze before final generation;
- both baselines receive identical evidence, constitution, target unit, and model family;
- conventional baseline cap equals the frozen multiplier, not observed final C cost;
- target scene is selected by predeclared position;
- condition labels, anchor identity, and presentation order are hidden/randomized;
- each supported primary assignment mode covers every scored triplet with exactly three judgments;
- every completed primary rater completes every forced-choice positive-control anchor; anchor `tie` values are schema-invalid;
- six-rater, five-rater, seven-rater timing-fallback, and three-rater full-coverage plans obey their declared per-rater caps;
- a failed timing pilot may trigger a seventh rater or shorter frozen scene, never reduced judgments per triplet;
- all technically valid samples are rated;
- anchor samples are rights-cleared, hash-verified, authored before primary generation, and cover each primary dimension exactly once;
- a failed anchor set produces `INCONCLUSIVE`, withholds scored preferences, and cannot authorize skill tuning; a technical anchor defect aborts/replaces the task before dataset freeze;
- raw agreement, nominal Krippendorff alpha, and tie rate are reported as diagnostics and cannot alone veto a run whose anchors pass;
- `scripts/m4_rules.py` is imported by both `analyze_m4.py` and `simulate_m4.py`;
- the simulator defaults to `--reliability-mode simulate`, is deterministic for a fixed seed, and every probability vector sums to one;
- a freeze artifact using `assume_interpretable` is rejected;
- the operating-characteristic artifact includes central/sensitivity scenarios, positive-control pass probability, a non-degenerate `INCONCLUSIVE` branch, repeat behavior, and required preference points;
- protocol freeze fails without a named operating-characteristic review, assumptions, rationale, and matching hashes;
- `scripts/analyze_m4.py` reproduces its checked-in example;
- aggregate primary thresholds apply against both baselines;
- per-brief robustness applies only to the stronger aggregate baseline and requires strict-majority direction on at least two briefs;
- secondary dimensions are non-gating and pre-sampled;
- degraded mode uses the same thresholds, full triplet coverage, completed forced-choice anchors, and a weaker-evidence label;
- results and exclusions are immutable after decision;
- one bounded MIXED repeat maximum, using only the committed reserve brief;
- the repeat uses five fresh runs per condition, the same affected-dimension thresholds, the frozen non-regression floor, no per-brief hurdle, and no pooled rounds;
- the expected cost calculation includes `P(MIXED) × 15` generated samples and repeat rating effort.

## 7. Audio/media tests

- voice identity/reference continuity;
- ASR text diff;
- ambience gap detection;
- cue continuity across shots;
- sample rate/channel/duration/loudness/true peak;
- A/V sync at known cue points;
- subtitle reading/timing limits;
- target editor round trip.

## 8. Release CI

```text
migration dry run
workflow compatibility/replay if applicable
rights and provider-policy validation
delivery/media validation
subtitle export
provenance sidecar/hash
NLE round trip
security/restore suite
staging approval
```

## 9. Completion evidence

Every milestone PR includes commands/results, failure-path evidence, fixture changes, public contract changes, and the exact exit-gate demonstration.

## INCONCLUSIVE reuse tests

- Frozen primary samples may be re-rated only when preference results were withheld, the unblinding map remained unopened, no creative-authority actor inspected conditions across labels, the creative pipeline is unchanged, a fresh rater pool is used, and labels are rerandomized.
- Any false or unknown attestation requires fresh primary briefs and samples.
- Changing prompts, skills, models, budgets, workflow, or sample selection forbids sample reuse even when the first analysis was withheld.
