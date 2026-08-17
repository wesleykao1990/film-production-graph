# M04 Story Room Decision Protocol — v2.4

**Purpose:** Decide whether the minimum Story Room creates enough additional writing value to justify completing the creative domain and investing in production tooling.

**Statistical status:** This is an internal, pre-registered **decision heuristic under uncertainty**. Its thresholds encode product risk appetite; they are not a claim of statistical significance or general efficacy. A powered follow-up is required before publishing efficacy claims.

## 1. Freeze lifecycle

The protocol has three states:

```text
draft → calibrated → frozen
```

Before freeze:

1. run one non-test calibration brief through all three conditions;
2. pilot the rating guide with at least two non-builder raters using samples that deliberately span a quality range;
3. verify that pilot raters identify the intended direction on every primary dimension; revise the guide or anchors if they do not;
4. measure completion time, scored-item tie rate, forced-choice anchor accuracy, rating ambiguities, and likely rater/brief heterogeneity;
5. project the Story Room cost per sample and freeze both baseline budgets;
6. create and hash the blinded positive-control anchor set before primary generation;
7. run `scripts/simulate_m4.py` with `--reliability-mode simulate`, calibration-informed central assumptions, and lower/higher sensitivity scenarios;
8. inspect PASS/MIXED/FAIL/**INCONCLUSIVE** behavior and the MIXED-repeat operating characteristics;
9. record a named review of the resulting `analysis/operating-characteristics.json`;
10. commit its hash together with the briefs, reserve commitment, assignment, prompts, anchor manifest, shared rule code, analysis code, simulation code, and decision rules.

Freeze is not permitted merely because the YAML validates. It is also not permitted when the checked simulation conditions away the `INCONCLUSIVE` branch. `assume_interpretable` may be run only as a secondary diagnostic that isolates the preference rule; it cannot satisfy the freeze requirement.

A named reviewer must inspect the simulated behavior at true preferences of at least 0.55, 0.65, and 0.75 and record why the false-positive, false-negative, and instrument-failure trade-offs are acceptable for this product decision. The simulation must show a **non-degenerate** `INCONCLUSIVE` probability under at least one plausible central or sensitivity scenario: neither forced to zero by assumption nor effectively one under every effect size.

One calibration brief cannot identify a uniquely correct variance model. Therefore the operating-characteristic artifact must include a central calibration-informed scenario plus lower- and higher-heterogeneity sensitivity scenarios. Do not tune assumptions until the desired decision appears.

Freeze occurs **before any final primary-brief generation**. After freeze, no prompt, skill, anchor, budget, rater rule, sample-selection rule, simulation assumption, or threshold may change. A technical abort may create a new protocol version only before anyone inspects primary outputs.

## 2. Hypothesis and target unit

Given the same Creative Constitution, Evidence Bank, brief, model family, and declared budget, independent raters will prefer the Story Room for:

1. specificity and non-substitutability;
2. character voice distinctiveness;
3. causal dramatic progression.

Each condition generates three connected screenplay scenes. Human rating uses the **pre-declared middle scene**, not a builder-selected excerpt, plus an identical neutral context card. The rated scene targets 2–3 screenplay pages. Full samples remain available for hard validators and secondary diagnostics.

## 3. Conditions

### A — Equal-information single-prompt baseline

A professionally written prompt receives the same constitution, evidence, brief, model family, target structure, and output requirements. It produces premise, characters, outline, and three scenes without the typed graph or repository skills.

### B — Fixed-budget conventional writer workflow

A conventional writer agent receives the same inputs and may revise, but it does not use independent candidate isolation, typed character/relationship state, Scene Contracts, or repository skills.

Its budget is frozen before final generation:

```text
projected_C_cap = calibration estimate including contingency
B_cap            = 1.5 × projected_C_cap
```

The multiplier intentionally favors the conventional baseline and avoids sizing B after observing C. Record the actual B:C cost ratio afterward.

### C — Minimum Film Production Graph Story Room

M04a includes only the workflow needed to test the three primary dimensions:

```text
Creative Constitution
Evidence Bank
independent premise candidates
selection rationale
characters and relationship state
causal beat graph
Scene Contract
scene realization/dialogue pass
subtext patch
hard validators
```

Compression, filmability, full voice audit, sequence authoring, setup/payoff tooling, Fountain export, and broad UI polish are M04b work after PASS.

## 4. Briefs and test-set isolation

Use:

- one non-scored calibration brief;
- three scored primary briefs with different domain/genre mechanics;
- one reserve brief for a MIXED repeat.

The reserve brief must be held outside the development-agent context. Before round one, commit:

```text
reserve brief ID
SHA-256 content commitment
custodian/location reference
creation timestamp
```

Do not reveal its contents to skill authors, prompt authors, or coding agents until a MIXED decision authorizes the repeat. The package supplies a commitment template, not a real secret brief.

All evidence must be synthetic or rights-cleared.

## 5. Run count and sample validity

Primary round:

```text
3 primary briefs
× 3 independent runs
× 3 conditions
= 27 scored story samples
```

The positive controls are fixed, synthetic evaluation samples; they are not additional A/B/C generations and are not included in the 27.

A sample is technically invalid only under pre-declared rules such as schema failure, missing required scene, provider outage before completion, or budget-cap breach. All valid samples are rated; the builder cannot select favorites.

Seeds and settings are recorded when available. Outputs, target-scene IDs, context cards, and hashes are frozen before assignment.

## 6. Presentation, anchors, and rater workload

A scored rating task is a **matched triplet**: A, B, and C outputs for one brief/run are displayed once under randomized labels. The confidential map asks only the two pairwise questions involving C, but the rater sees opaque sample labels and never sees condition identity. Unblinding occurs only during analysis.

Each primary rater also completes two blinded positive-control tasks interspersed with the scored tasks. The controls must:

- use the same display format and approximate length as scored material;
- remain hidden as controls until analysis;
- include one intact scene and deliberately degraded variants;
- cover each primary dimension exactly once;
- be strong enough to test comprehension of the rubric without becoming absurdly obvious;
- use **forced choice** between the two displayed samples; anchors do not offer a substantive tie response;
- provide a separate “report technical problem” action that aborts and replaces the task before dataset freeze rather than recording a tie;
- be authored and frozen before primary outputs are generated.

### Standard modes

```text
target qualified raters          = 6
minimum qualified raters         = 5
each scored triplet rated by     = 3 raters
each anchor completed by         = every primary rater
target completion time           <= 45 minutes per rater, anchors included
```

The default six-rater assignment gives each rater at most five scored triplets. A frozen five-rater recruitment fallback permits at most six. If the timing pilot shows that five triplets plus controls cannot fit within 45 minutes, the permitted responses are:

1. recruit a seventh qualified rater and use the supplied four-triplet assignment; or
2. shorten the rated scene within the predeclared page range.

Do **not** reduce ratings per triplet. That would silently create a different experiment.

A qualified rater must be independent of implementation and sample authorship, fluent enough to judge the screenplay language, complete the dimension-orientation pilot, and have no prior access to final condition outputs, anchor identities, or the unblinding map. Record conflicts, withdrawals, and exclusions before analysis.

### Degraded three-rater mode

Use only when five qualified raters cannot be recruited after documented attempts:

```text
qualified raters                 = 3
each scored triplet rated by     = all 3 raters
scored triplets per rater        = 9
anchors per rater                = 2
delivery                         = up to two sessions of <=45 minutes
evidence_strength                = degraded_rater_diversity
```

This mode restores three judgments per triplet instead of combining less information with an unreachable higher threshold. It uses the same numerical decision rule as standard mode. Its smaller and less diverse rater pool remains visible in every report and blocks public efficacy claims without a powered follow-up.

## 7. Rating dimensions

### Gating primary dimensions

- **Specificity/non-substitutability:** Could names, setting, profession, and objects be swapped without materially changing the dramatic mechanism?
- **Character voice:** Do characters use distinguishable tactics, syntax, rhythm, omissions, and relationship-specific behavior?
- **Causal progression:** Do choices under pressure cause turns and state changes rather than events merely occurring in sequence?

### Non-gating secondary dimensions

- coherence/comprehensibility;
- relationship pressure;
- subtext;
- emotional engagement;
- predictability/cliché risk.

Secondary dimensions are rated only on a preselected subsample of at most two assigned triplets per rater. They are reported separately and cannot cause PASS or FAIL.

Hard validators remain separate:

- objective/opposition/turn/state-delta completeness;
- knowledge-continuity violations;
- unsupported entity/fact introduction;
- bounded-patch violations.

No blended creative score is calculated.

## 8. Instrument validity and reliability diagnostics

### 8.1 Pilot positive control

The pilot must deliberately include strong and weak examples. At least two non-builder raters must identify the intended direction for all three primary dimensions and explain the distinction in their own words. If either rater misses a target direction, revise the wording, sample length, or degradation recipe before freeze. Pilot results are developmental and are not pooled with the primary round.

### 8.2 Blinded primary-round positive controls

The primary round uses the frozen anchor tasks. Every completed primary rater must rate every anchor. Anchor questions are **forced choice**: choose which sample is stronger on the named dimension. A substantive tie option is not shown because the control contains a deliberately large, known contrast. If a sample fails to render, is inaccessible, or has another technical defect, the rater reports the problem; that assignment is aborted and replaced before the rating dataset is frozen. A technical abort is never encoded as a tie or as a degraded-scene preference.

The instrument is valid only when:

- for each primary dimension, a strict majority of all completed anchor judgments favors the intact scene;
- pooled across dimensions, at least 75% of all anchor judgments favor the intact scene;
- every completed primary rater has one valid forced-choice judgment for every assigned anchor dimension.

If the positive control fails, the result is `INCONCLUSIVE`. Scored preference percentages are not computed or exposed, and the run cannot be used to tune creative skills.

An instrument-side `INCONCLUSIVE` requires a new protocol version, but it does **not automatically consume the primary briefs or frozen samples**. Re-rating the same frozen samples is permitted only when all of the following are attested and audit-logged:

1. scored preference results were withheld by code;
2. the condition-to-label unblinding map was never opened;
3. no person or agent with authority to revise prompts, skills, models, budgets, or sample-selection rules inspected or compared outputs across conditions;
4. the creative pipeline is unchanged and only the measurement instrument, rater orientation, or rater pool is repaired;
5. the rerun uses a completely fresh rater pool and newly randomized opaque labels.

When any attestation is false or unknown—or when a creative prompt, skill, model, budget, workflow, or selection rule changes—the rerun must use fresh primary briefs and fresh samples. This reuse policy saves material only after a genuinely blinded instrument failure; it must never become a way to tune against held-out work.

### 8.3 Agreement diagnostics are not gates

For each primary dimension, still report:

- raw exact pairwise agreement;
- nominal Krippendorff’s alpha, with tie as a category;
- missingness and tie rate.

These values diagnose rubric ambiguity and rater behavior, but they **do not by themselves trigger `INCONCLUSIVE`**. Chance-corrected agreement can approach zero when condition preference is uniform across items because the marginal distribution explains the apparent agreement—the prevalence paradox. A consistently superior system must not be rejected merely because scored items offer little item-level variance.

Unusual diagnostics must still be discussed in the human decision record. They may motivate a future powered study, but they cannot silently replace the frozen positive-control rule.

## 9. Operating-characteristic precondition

The package ships:

```text
scripts/m4_rules.py       shared pure preference and anchor rules
scripts/analyze_m4.py     applies them to real ratings
scripts/simulate_m4.py    estimates behavior before protocol freeze
```

Both executable paths import `m4_rules.py`. A rule change changes the stored `rule_source_hash` and mechanically invalidates a stale calibration artifact.

At minimum, run the central and sensitivity scenarios at true preferences 0.55, 0.65, and 0.75 with at least 4,000 trials per point using:

```bash
python scripts/simulate_m4.py \
  --protocol examples/evals/story-room-gate/protocol.yaml \
  --assignment-plan examples/evals/story-room-gate/assignment-plan.example.yaml \
  --run-mode standard_six \
  --trials 4000 \
  --true-preferences 0.55 0.65 0.75 \
  --reliability-mode simulate \
  --output examples/evals/story-room-gate/analysis/operating-characteristics.json
```

Record:

- primary PASS/MIXED/FAIL/INCONCLUSIVE probabilities;
- forced-choice positive-control pass probability and assumed anchor accuracy;
- diagnostic mean agreement, alpha, and scored-item tie rate;
- conditional MIXED-repeat pass probability;
- eventual PASS probability;
- central and sensitivity assumptions;
- repeat run count;
- named human review and rationale.

A freeze artifact produced with `assume_interpretable` is invalid. That mode may be retained only to isolate how much behavior comes from the preference rule versus the instrument control.

Reject or revise the planned design before freeze when, under plausible assumptions:

- a worthless system has an unacceptably high eventual-PASS probability;
- a meaningfully better system has an unacceptably low eventual-PASS probability;
- `INCONCLUSIVE` is nearly zero only because it was assumed away;
- `INCONCLUSIVE` is close to one across all plausible effect sizes;
- the MIXED repeat is materially harder than the primary aggregate rule;
- degraded mode cannot reach a decision despite full triplet coverage.

Simulation is calibration, not proof. It does not turn the M04 gate into a powered hypothesis test.

## 10. Decision rule

For **scored A/B/C comparisons**, ties are excluded from the preference denominator and reported separately. Positive-control anchors are forced choice and have no tie category.

### PASS

The Story Room must satisfy all of the following:

1. the blinded positive-control instrument passes;
2. aggregate preference clears the frozen threshold against **both** baselines:
   - specificity ≥ 60%;
   - character voice ≥ 60%;
   - causal progression ≥ 55%;
3. for each primary dimension, Story Room receives a strict majority against the **stronger aggregate baseline** on at least two of three briefs;
4. hard-continuity violations are no worse than the best baseline.

The stronger baseline is the aggregate comparison with lower Story Room preference for that dimension. A numerical tie resolves to the fixed-budget conventional arm.

This deliberately separates two jobs:

```text
aggregate threshold  = required magnitude of improvement
per-brief majority    = evidence that direction is not isolated to one lucky brief
```

### MIXED

`MIXED` means the instrument is valid and at least one—but not all—primary requirements passes, or the continuity non-inferiority condition prevents an otherwise complete PASS.

A MIXED result permits exactly one bounded revision:

1. identify one skill or contract responsible for the affected dimensions;
2. revise it once using calibration/development material only;
3. reveal the committed reserve brief;
4. freeze five fresh A/B/C runs on the reserve brief—15 new story samples;
5. use three ratings per fresh triplet;
6. apply the same aggregate threshold to each affected dimension against both baselines;
7. require previously passing dimensions to remain at or above 50% against both baselines;
8. apply no extra per-brief hurdle;
9. keep round-one and repeat results separate; never pool across the revision boundary.

If the same qualified rater pool and unchanged instrument are used, the primary-round positive-control result may be inherited. Any new rater must complete the anchors, and the control must be re-evaluated across the actual repeat rater pool before preferences are read.

The repeat produces PASS only when all affected thresholds, non-regression floors, continuity, and instrument requirements pass. Otherwise it returns FAIL or INCONCLUSIVE as appropriate.

### FAIL

`FAIL` means the instrument is valid but the frozen preference/continuity rule does not support expansion, including a failed MIXED repeat.

Required action:

- stop platform expansion;
- inspect which dimensions failed;
- decide whether the thesis is wrong or whether the graph should be repositioned as continuity, provenance, pre-production, and production-management tooling.

### INCONCLUSIVE

`INCONCLUSIVE` means the rating instrument failed its positive control, required data are missing, or the protocol was violated. It is **not** evidence that the creative thesis failed and does not authorize creative-skill tuning from the scored outputs.

Required action:

- quarantine scored preference results from product decisions;
- identify and repair the measurement defect;
- issue a new protocol version;
- use a completely fresh rater pool and newly randomized labels;
- re-rate the frozen primary samples only when every reuse attestation in §8.2 is true and audit-logged;
- otherwise use fresh primary briefs and fresh samples.

## 11. Cost and logistical reporting

Report the primary round and expected MIXED path separately:

```text
primary generated samples = 27
reserve repeat if MIXED    = 15
maximum generated samples  = 42, excluding calibration/technical aborts
```

Because MIXED can be the modal primary outcome under plausible effects, budget planning must include:

```text
expected samples = 27 + P(MIXED) × 15
expected rating cost = primary rating cost + P(MIXED) × repeat rating cost
```

Do not price the repeat as a remote contingency. The operating-characteristic artifact supplies the planning probability.

Every report must include:

- generated samples by condition and round;
- fixed caps and actual cost ratios;
- invalid technical runs and reasons;
- rater compensation and workload;
- direct versus eventual PASS;
- evidence-strength label;
- provider/model resolution and latency.

## 12. Parallel speaking-character feasibility spike

If the intended first film shows a recurring character speaking on camera, run a manual 5–15-second production feasibility spike in parallel with M04a. This requires no platform code.

Record:

- target language and locked line;
- reference image and rights status;
- provider, resolved model, and settings;
- native-dialogue or canonical-audio/lip-sync path;
- ASR transcript and screenplay diff;
- voice identity, mouth synchronization, and face stability;
- **total attempts and attempts to first acceptable take**;
- acceptable-take count and rejection categories;
- cost and latency per attempt and in total;
- realistic maximum line length;
- verdict: viable / viable_with_constraints / alternate_path_required / not_viable;
- consequences for M06/M07 and the film cost projection.

Define “acceptable take” before the first generation. M07 later productionizes the selected path.

## 13. Required repository artifacts

```text
examples/evals/story-room-gate/
  protocol.yaml
  rater-guide.md
  assignment-plan.example.yaml
  rating_form.schema.json
  run-manifest.example.yaml
  ratings.example.jsonl
  decision-template.md
  reserve-brief-commitment.template.yaml
  baseline_equal_information.md
  baseline_fixed_budget.md
  anchors/
    anchor-manifest.example.yaml
    intact-scene.example.md
    degraded-specificity-voice.example.md
    degraded-causality.example.md
  briefs/
    calibration.yaml
    blue-pen.yaml
    closed-platform.yaml
    genre-contrast.yaml
  analysis/
    operating-characteristics.example.json

scripts/
  m4_rules.py
  analyze_m4.py
  simulate_m4.py
```

The checked-in ratings, analysis, and operating-characteristic outputs are **mechanical fixtures only**. They prove that schemas, decisions, positive controls, hashing, and scripts agree. They are not evidence that the real Story Room has passed.
