# Milestone M04a — Minimum Story Room and decision gate

Implement only the minimum creative workflow required to test specificity, character voice, and causal progression. Do not implement M04b passes, Fountain export, production providers, durable orchestration, or the full lineage canvas.

## Build

1. implement Creative Constitution and Evidence Bank inputs;
2. implement independent premise candidates and a recorded human selection rationale;
3. implement character, relationship, causal beat, Scene Contract, scene realization/dialogue, and subtext-patch artifacts;
4. run deterministic hard validators for objective/opposition/turn/state delta, knowledge continuity, unsupported facts/entities, and patch scope;
5. implement the minimal review interface needed for candidate selection, artifact approval, matched-triplet rating, and decision inspection;
6. implement the frozen M04 analyzer, simulator, and shared pure rule module;
7. freeze fixed budgets, three primary briefs, reserve commitment, rater guide, assignments, prompts, target-scene rule, randomized mappings, positive-control anchors, and decision branches;
8. run a deliberately varied two-rater instrument/timing pilot;
9. run operating-characteristic simulation with `--reliability-mode simulate`, central and sensitivity assumptions, and named review;
10. execute the primary gate only after every freeze precondition passes;
11. run the manual speaking-character feasibility spike in parallel when the first film requires visible dialogue.

## Required experiment behavior

- Conditions A, B, and C receive equivalent source material and model-family access.
- Condition B uses a fixed precommitted budget derived from calibration, not observed C outputs.
- Every valid primary output is rated; no builder selection is allowed.
- Every primary rater completes the blinded, forced-choice anchor controls; anchor ties are impossible in the rating schema, while technical defects abort and replace the task before freeze.
- Anchor failure yields `INCONCLUSIVE` and withholds scored preference results.
- Raw agreement and Krippendorff alpha remain reported diagnostics, not gates.
- Aggregate thresholds apply against both baselines.
- Per-brief robustness uses a strict majority against only the stronger aggregate baseline on at least two briefs.
- A MIXED repeat freezes five new A/B/C runs on the sealed reserve brief, applies no extra per-brief rule, and never pools pre- and post-revision data.
- Degraded mode preserves three ratings per triplet and carries a weaker-evidence label instead of unreachable thresholds.

## Tests

- Analyzer and simulator import the same rule module.
- Mutating the rule source invalidates the operating-characteristic artifact hash.
- Example forced-choice anchors pass; deliberately wrong anchor selections produce `INCONCLUSIVE` and withheld preferences; anchor records containing `tie` fail schema/analysis validation.
- Low scored-item alpha cannot alone produce `INCONCLUSIVE` when anchors pass.
- Missing scored or anchor assignments fail analysis; technical anchor problems must be replaced before dataset freeze rather than scored.
- Simulator defaults to `simulate`; checked freeze artifacts using `assume_interpretable` are rejected.
- Operating-characteristic probabilities normalize and include a non-degenerate `INCONCLUSIVE` branch under at least one plausible scenario, using forced-choice anchor accuracy rather than an anchor tie-rate assumption.
- Standard-seven, standard-six, standard-five, and degraded-three assignments preserve three ratings per scored triplet.
- Five-run reserve-repeat assignments are complete and within workload limits.
- The equal-information and fixed-budget baselines are reproducible from frozen prompts and inputs.
- The speaking-character spike records attempts to first acceptable take and rejection categories.

## Exit gate

Return exactly one frozen product decision:

```text
PASS          → implement M04b, then proceed toward production
MIXED         → one bounded revision and one five-run reserve-brief repeat
FAIL          → stop expansion and reassess/reposition the thesis
INCONCLUSIVE  → repair measurement under a new protocol; reuse frozen samples only after all blinding/reuse attestations pass, otherwise use fresh briefs
```

Provide the protocol hash, rule hash, anchor-manifest hash, simulation hash, assignment mode, valid sample counts, positive-control result, non-gating diagnostics, preference/continuity results when permitted, costs, rater workload, dialogue-spike evidence, and exact next action. Stop after the M04a decision; do not begin M04b in the same branch.
