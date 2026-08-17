# M04a Story Room Decision

## Frozen inputs

- Protocol version and hash:
- Shared rule-code version and hash:
- Analysis-code version and hash:
- Simulation-code version and hash:
- Operating-characteristics artifact hash:
- Operating-characteristics reviewed by / at:
- Review rationale and accepted risk trade-off:
- Anchor-manifest hash:
- Baseline prompt hashes:
- Skill-lock hash:
- Primary-brief hashes:
- Reserve-brief commitment hash:
- Provider/model price snapshot:
- Projected Story Room cap per sample:
- Frozen Condition B cap per sample:
- Assignment mode: standard-seven / standard-six / standard-five / degraded-three:

## Operating-characteristic review

All freeze-eligible calculations must use `reliability_mode: simulate`.

| True C preference | PASS | MIXED | FAIL | INCONCLUSIVE | Eventual PASS | Instrument pass |
|---:|---:|---:|---:|---:|---:|---:|
| 0.55 | | | | | | |
| 0.65 | | | | | | |
| 0.75 | | | | | | |

- Scored-item tie-rate assumption and source:
- Rater-effect assumption and source:
- Brief-effect assumption and source:
- Anchor intact-preference assumption and source:
- Forced-choice anchor intact-preference assumption and source:
- Sensitivity scenarios:
- MIXED-repeat runs per condition:
- Conditional MIXED-repeat PASS behavior:
- Why the estimated false-positive, false-negative, and INCONCLUSIVE behavior was accepted:

## Execution

- Valid samples by condition:
- Technically invalid samples and predeclared reason:
- Qualified raters completed:
- Missing assignments:
- Median and maximum rater duration, anchors included:
- Evidence strength: standard / degraded_rater_diversity:

## Blinded positive-control instrument check

| Dimension | Intact | Degraded | Intact preference | Passed? |
|---|---:|---:|---:|---|
| Specificity | | | | |
| Character voice | | | | |
| Causal progression | | | | |

- Anchor response mode: forced choice
- Technical anchor aborts/replacements before freeze:
- Pooled intact preference:
- Instrument valid: yes / no

A failed positive control makes the result `INCONCLUSIVE` and withholds scored preference results from the product decision.

## Scored-item reliability diagnostics — non-gating

| Dimension | Raw agreement | Krippendorff α | Tie rate | Notes |
|---|---:|---:|---:|---|
| Specificity | | | | |
| Character voice | | | | |
| Causal progression | | | | |

These values are reported for diagnosis only. They are not hard gates because skewed preference marginals can drive chance-corrected agreement toward zero even under consistent superiority.

## Primary preferences

Report C versus A and C versus B separately. The stronger baseline is the aggregate comparison with lower C preference. Aggregate thresholds apply against both baselines; per-brief robustness asks only for a strict majority against the stronger baseline on at least two briefs.

| Dimension | C vs A | C vs B | Stronger baseline | Briefs with >50% vs stronger baseline | Requirement passed? |
|---|---:|---:|---|---:|---|
| Specificity | | | | | |
| Character voice | | | | | |
| Causal progression | | | | | |

- Hard-continuity violations, C:
- Hard-continuity violations, best baseline:
- Continuity non-inferiority met: yes / no

## Non-gating diagnostics

- Secondary-dimension subsample summary:
- Cost by condition and actual B:C ratio:
- Latency by condition:
- Human interventions:
- Full regenerations versus patches:

## Parallel dialogue-feasibility evidence

- Applicable: yes / no
- Path tested:
- Predeclared acceptable-take definition:
- Total attempts:
- Attempts to first acceptable take:
- Acceptable-take rate:
- Rejection categories:
- Cost implication for film projection:
- Resulting M06/M07 policy:

## Decision

- Decision: `PASS` / `MIXED` / `FAIL` / `INCONCLUSIVE`
- Direct or eventual decision:
- Frozen rule applied:
- Rationale:
- Permitted next action:
- Prohibited next action:

For `MIXED`, identify exactly one skill or contract eligible for revision. Freeze five fresh A/B/C runs on the reserve brief, use the same affected-dimension thresholds, protect previously passing dimensions at 50%, add no per-brief hurdle, and do not pool rounds.

For `INCONCLUSIVE`, identify the measurement defect and do not tune creative skills from the withheld result. Record the following reuse attestations before deciding whether frozen samples may be re-rated:

- preference results were withheld by code: yes / no;
- unblinding map was never opened: yes / no;
- no cross-condition inspection by anyone with creative-change authority: yes / no;
- creative pipeline remains unchanged: yes / no;
- fresh rater pool and newly randomized labels planned: yes / no.

Reuse the frozen primary samples only when every answer is yes. Otherwise use fresh primary briefs and samples.
