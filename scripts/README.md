# Package scripts

These scripts make the review-critical parts executable without creating an application runtime.

- `validate_package.py` parses YAML/JSON, validates every JSON Schema and mapped fixture, verifies whole-package skill locking, validates assignments, anchors, operating-characteristic artifacts, and internal links, runs the M04 example analysis, and optionally verifies `CHECKSUMS.sha256`.
- `m4_rules.py` contains the pure frozen M04 preference and positive-control rules. It performs no file I/O.
- `analyze_m4.py` validates scored and anchor coverage, checks the blinded positive control before exposing preferences, unblinds pairwise ratings, calculates preferences, non-gating agreement diagnostics, continuity, cost/latency, and the frozen heuristic decision.
- `simulate_m4.py` imports the same rule functions and estimates PASS/MIXED/FAIL/INCONCLUSIVE behavior—including the anchor control and five-run MIXED repeat—before protocol freeze.

## Schema registry requirement

Schemas use non-network URN identifiers such as:

```text
urn:film-production-graph:schema:shot-contract:2
```

Collection schemas reference those URNs. Validate with the bundled registry built from every schema in `schemas/`; do not instantiate an isolated `Draft202012Validator` without that registry. A naive isolated validator may treat the URN as unresolved and can attempt an inappropriate network resolution before failing.

`validate_package.py` demonstrates the supported pattern using `referencing.Registry` and `Resource`.

## M04 reliability rule

The real freeze must simulate the positive-control instrument:

```text
--reliability-mode simulate
```

The legacy-named `assume_interpretable` mode remains only as a diagnostic for isolating the preference rule. It mechanically forces instrument validity and therefore cannot produce a freeze-eligible calibration artifact.

Raw pairwise agreement and nominal Krippendorff alpha on scored items are reported, but they are not hard gates. The blinded anchor control is the instrument-validity gate because chance-corrected agreement can collapse under skewed marginals even when raters consistently prefer one condition.

Anchor records are forced choice. The rating schema and analyzer accept only `left` or `right`; a technical rendering/accessibility problem must abort and replace the task before freeze and is never serialized as a tie. The simulator therefore models anchor accuracy and heterogeneity but has no anchor tie-rate parameter.

After instrument-side `INCONCLUSIVE`, `m4_rules.evaluate_inconclusive_reuse` permits re-rating frozen samples only when all blinding attestations are affirmatively true, the creative pipeline is unchanged, a fresh rater pool is used, and labels are re-randomized. Missing or uncertain evidence selects fresh briefs and samples.

## Commands

Run from the package root:

```bash
python scripts/validate_package.py

python scripts/analyze_m4.py \
  --protocol examples/evals/story-room-gate/protocol.yaml \
  --manifest examples/evals/story-room-gate/run-manifest.example.yaml \
  --ratings examples/evals/story-room-gate/ratings.example.jsonl \
  --output /tmp/m4-analysis.json

python scripts/simulate_m4.py \
  --protocol examples/evals/story-room-gate/protocol.yaml \
  --assignment-plan examples/evals/story-room-gate/assignment-plan.example.yaml \
  --run-mode standard_six \
  --trials 4000 \
  --true-preferences 0.55 0.65 0.75 \
  --reliability-mode simulate \
  --output /tmp/m4-operating-characteristics.json

python -m unittest discover -s scripts/tests -v

cd prototype
python -m pytest
python -m app.cli smoke
```

The checked-in simulation and analysis outputs are mechanical fixtures. They do not claim inferential significance or prove creative efficacy. Before a real M04 freeze, replace simulation assumptions with calibration-informed central and sensitivity values, confirm that `INCONCLUSIVE` is neither assumed away nor forced, and record a named human review and rationale.
