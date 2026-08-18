# M04a operating-characteristics review (draft template)

**Status:** `draft` — this form is a blank review instrument, not a simulation
result, a freeze attestation, or a product decision.

Complete a controlled copy only after the authoritative simulator has been run
with `--reliability-mode simulate`. Keep the controlled copy and raw output in
the protected packet, outside ordinary development-agent context. This
repository template must remain a draft. Do not put reserve-brief contents,
condition-to-label mappings, rater identities, credentials, or unblinded
primary results in this form.

If an authorized protected provider call is needed, supply the secret at
execution through the named environment variable `M04A_PROVIDER_SECRET`; never
record its value or create a credential-value field here.

## Record header

- Record type: `M04A_OPERATING_CHARACTERISTICS_REVIEW`
- Template version: `REPLACE_BEFORE_EXECUTION`
- Record status: `draft`
- Protected packet reference: `null`
- Review record reference: `null`
- Prepared by role reference: `REPLACE_BEFORE_EXECUTION`
- Prepared at: `null`
- Protocol version: `REPLACE_BEFORE_FREEZE`
- Assignment mode: `REPLACE_BEFORE_FREEZE`
- Product decision: `null` — record exactly one decision only in the completed decision record.

## Execution contract

Record references and hashes in a controlled copy; do not paste large raw
simulation output into this form.

| Required control | Draft value | Evidence/reference to supply before freeze |
| --- | --- | --- |
| Protocol source | `examples/evals/story-room-gate/protocol.yaml` | `REPLACE_BEFORE_FREEZE` |
| Protocol content hash | `null` | `REPLACE_BEFORE_FREEZE` |
| Assignment-plan source | `examples/evals/story-room-gate/assignment-plan.example.yaml` | `REPLACE_BEFORE_FREEZE` |
| Assignment-plan content hash | `null` | `REPLACE_BEFORE_FREEZE` |
| Shared rule source | `scripts/m4_rules.py` | `REPLACE_BEFORE_FREEZE` |
| Shared rule source hash | `null` | `REPLACE_BEFORE_FREEZE` |
| Simulator source | `scripts/simulate_m4.py` | `REPLACE_BEFORE_FREEZE` |
| Simulator source hash | `null` | `REPLACE_BEFORE_FREEZE` |
| Analyzer source | `scripts/analyze_m4.py` | `REPLACE_BEFORE_FREEZE` |
| Analyzer source hash | `null` | `REPLACE_BEFORE_FREEZE` |
| Positive-control anchor manifest reference | `null` | `REPLACE_BEFORE_FREEZE` |
| Positive-control anchor manifest hash | `null` | `REPLACE_BEFORE_FREEZE` |
| Calibration record reference | `null` | `REPLACE_BEFORE_FREEZE` |
| Protected simulation output reference | `null` | `REPLACE_BEFORE_FREEZE` |
| Protected simulation output hash | `null` | `REPLACE_BEFORE_FREEZE` |

The source paths above are authoritative package paths. A checked-in example
output is a mechanical fixture only and cannot be used as the freeze artifact.

## Required simulation invocation

The following is a command shape, not evidence that a run occurred. Replace
only the output/reference placeholders with protected paths and preserve the
invocation in the command log:

```text
python scripts/simulate_m4.py \
  --protocol examples/evals/story-room-gate/protocol.yaml \
  --assignment-plan examples/evals/story-room-gate/assignment-plan.example.yaml \
  --run-mode REPLACE_BEFORE_FREEZE \
  --trials 4000 \
  --true-preferences 0.55 0.65 0.75 \
  --reliability-mode simulate \
  --output REPLACE_BEFORE_FREEZE
```

- Command-log reference: `null`
- Actual run mode: `REPLACE_BEFORE_FREEZE`
- Reliability mode: `simulate` (a freeze-eligible artifact cannot use `assume_interpretable`)
- Trials per true-preference point: `4000` minimum; actual count: `null`
- True-preference points: `0.55`, `0.65`, `0.75`
- Simulation completed at: `null`
- Simulation exit/status reference: `null`
- Any technical abort and reason: `null`

## Calibration-informed assumptions

Use the non-test calibration record and pilot evidence to justify a central
scenario. Add lower- and higher-heterogeneity sensitivity scenarios. Do not
tune assumptions until a desired decision appears. A null value is unresolved,
not an assumption of zero.

| Scenario | Scenario source/reference | Tie rate | Rater heterogeneity (logit SD) | Brief heterogeneity (logit SD) | Anchor intact preference | Anchor rater heterogeneity (logit SD) | Continuity pass assumption | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Central calibration-informed | `null` | `null` | `null` | `null` | `null` | `null` | `null` | `REPLACE_BEFORE_FREEZE` |
| Lower heterogeneity sensitivity | `null` | `null` | `null` | `null` | `null` | `null` | `null` | `REPLACE_BEFORE_FREEZE` |
| Higher heterogeneity sensitivity | `null` | `null` | `null` | `null` | `null` | `null` | `null` | `REPLACE_BEFORE_FREEZE` |

Additional simulator assumptions (for example, run/dimension effects,
technical invalidity, and anchor-dimension variation):

`REPLACE_BEFORE_FREEZE`

Assumption provenance and calibration limitations:

`REPLACE_BEFORE_FREEZE`

## Primary operating-characteristic results

Copy the simulator's values into the protected review record. Leave this
repository template blank. Results must include PASS/MIXED/FAIL/INCONCLUSIVE,
instrument-pass, and eventual-PASS probabilities at all three required points
for every central and sensitivity scenario.

| Scenario | True C preference | PASS | MIXED | FAIL | INCONCLUSIVE | Eventual PASS | Instrument pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Central calibration-informed | 0.55 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Central calibration-informed | 0.65 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Central calibration-informed | 0.75 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Lower heterogeneity sensitivity | 0.55 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Lower heterogeneity sensitivity | 0.65 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Lower heterogeneity sensitivity | 0.75 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Higher heterogeneity sensitivity | 0.55 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Higher heterogeneity sensitivity | 0.65 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| Higher heterogeneity sensitivity | 0.75 | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |

Probability normalization/check reference: `null`

Non-degenerate `INCONCLUSIVE` branch observed under a plausible scenario:
`null` (must not be forced to zero or effectively one under every point)

If the condition is not met, freeze is blocked. Record the defect and protocol
revision need; do not alter the thresholds or hide the branch.

## Diagnostic and MIXED-repeat results

These are operating-characteristic diagnostics, not completed primary ratings.
They must remain separate from the product decision and must not be used to
silently replace the frozen rules.

### Reliability diagnostics

| Scenario / true preference | Dimension | Mean raw agreement | Mean nominal Krippendorff alpha | Mean scored-item tie rate | Evidence/reference |
| --- | --- | ---: | ---: | ---: | --- |
| `REPLACE_BEFORE_FREEZE` | specificity | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| `REPLACE_BEFORE_FREEZE` | character_voice | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |
| `REPLACE_BEFORE_FREEZE` | causal_progression | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` | `REPLACE_BEFORE_FREEZE` |

Low alpha or unusual agreement is diagnostic only. It cannot independently
produce `INCONCLUSIVE` when the positive-control instrument passes.

### MIXED repeat behavior

- Repeat runs per condition: `5`
- Repeat ratings per triplet: `3`
- Conditional MIXED-repeat trial count by scenario/point: `REPLACE_BEFORE_FREEZE`
- Conditional MIXED-repeat PASS probability by scenario/point: `REPLACE_BEFORE_FREEZE`
- Eventually-PASS calculation reference: `null`
- Repeat rule/round-separation check reference: `null`
- Any scenario in which the repeat is materially harder than the primary rule:
  `REPLACE_BEFORE_FREEZE`

## Named human review

The named reviewer must inspect the central and both sensitivity scenarios at
0.55, 0.65, and 0.75, including the instrument-failure and MIXED-repeat
behavior. This is a human review of a simulation, not an agent approval and not
a product decision.

- Reviewer role: `REPLACE_BEFORE_FREEZE`
- Reviewer identity reference: `null`
- Reviewed at: `null`
- Review status: `null`
- Review attestation/reference: `null`
- False-positive trade-off accepted? `null`
- False-negative trade-off accepted? `null`
- Measurement-failure / `INCONCLUSIVE` trade-off accepted? `null`
- Rationale for accepting or rejecting the planned design:

  `REPLACE_BEFORE_FREEZE`

- Required protocol, assignment, instrument, or threshold revision:

  `REPLACE_BEFORE_FREEZE`

- Reviewer unresolved questions:

  `REPLACE_BEFORE_FREEZE`

## Freeze-readiness checklist

Leave unchecked in this repository template. A controlled copy may check an item
only when its evidence reference is present.

- [ ] `REPLACE_BEFORE_FREEZE`: calibration-informed central assumptions recorded.
- [ ] `REPLACE_BEFORE_FREEZE`: lower- and higher-heterogeneity sensitivity scenarios run.
- [ ] `REPLACE_BEFORE_FREEZE`: at least 4,000 trials used at each required point.
- [ ] `REPLACE_BEFORE_FREEZE`: reliability mode is `simulate`.
- [ ] `REPLACE_BEFORE_FREEZE`: forced-choice anchor accuracy is modeled; no anchor tie-rate assumption is used.
- [ ] `REPLACE_BEFORE_FREEZE`: PASS/MIXED/FAIL/INCONCLUSIVE and eventual-PASS probabilities are recorded.
- [ ] `REPLACE_BEFORE_FREEZE`: `INCONCLUSIVE` is non-degenerate under a plausible scenario.
- [ ] `REPLACE_BEFORE_FREEZE`: MIXED repeat uses five runs per condition and remains separate from round one.
- [ ] `REPLACE_BEFORE_FREEZE`: named human review and risk rationale are complete.
- [ ] `REPLACE_BEFORE_FREEZE`: output and source hashes are captured in the protected packet.
- [ ] `REPLACE_BEFORE_FREEZE`: no reserve contents, unblinding map, credential value, or primary result appears here.

## Handoff and blockers

- Freeze readiness: `null`
- Protocol custodian review reference: `null`
- Protected packet manifest reference: `null`
- Blockers:

  `REPLACE_BEFORE_FREEZE`

- Next operator action:

  `REPLACE_BEFORE_FREEZE`

- This form authorizes no primary generation, no rater unblinding, no creative
  tuning, no M04b work, and no product decision.
