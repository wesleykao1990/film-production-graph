# Effort and Cost Model — Final reviewed specification

## 1. Assumption

The plan assumes one product owner/filmmaker working with repository-capable coding agents, with human review of architecture, migrations, security boundaries, and creative evaluation.

It is not a calendar commitment. Effort bands communicate subsystem weight and prevent a coding agent from treating every milestone as comparable.

## 2. Bands

| Band | Meaning | Typical coding-agent cycles |
|---|---|---:|
| S | Isolated contract, utility, or narrow vertical slice | 1–2 |
| M | Several related components with integration tests | 3–5 |
| L | Substantial subsystem crossing database/API/UI/runtime boundaries | 6–10 |
| XL | Platform within the platform; split into multiple PRs | 10+ |

A cycle means one scoped implementation pass, review/hardening pass, and exit-gate evidence—not elapsed days.

## 3. Milestone weight

| Milestone | Band | Why |
|---|---:|---|
| M00 Foundation Lite | M | Monorepo, database, CI, fakes, local commands |
| M01 Artifact/lineage/impact | L | Core domain, migrations, concurrency, RLS-ready design |
| M02 Repository skills | M | Loader, validation, whole-package lock, routing tests |
| M03 Agent runtime/security | L | Typed tools, model fakes, provenance, adversarial corpus |
| M04a Minimum Story Room/gate | L–XL | Minimum creative workflow, rating UI, executable calibration, anchors, and human decision protocol |
| M04b Story Room completion | M | Deferred passes, exports, and UI polish only after PASS |
| M05 Durable runtime | L | ADR, resumability, approvals, idempotency |
| M06 Audio/delivery/rights | L | Several media domains plus validators |
| M07 Animatic/productionized dialogue path | L | Shot planning, media assembly, repeatable dialogue workflow |
| M08 Minimum finished film | M–L | Manual adapter, real assets, release validation |
| M09 Automated providers | L per provider family | Provider contracts are shared; adapters remain substantial |
| M10 Full Studio/edit/export | XL | Graph UI, timeline, OTIO, release provenance |
| M11 Evaluation/observability | L | Repeated runs, cost/latency, dashboards, regressions |
| M12 Hosted product hardening | XL | Registry, tenancy, roles, recovery, security operations |

The manual speaking-character spike parallel to M04a is an experiment, not an engineering milestone: one reference, one locked line, one or two provider paths, an honest decision record, and observed attempts to first acceptable take. That yield measurement is the earliest reality check on the film-cost envelope.

## 4. Planning cost envelope — M04a gate

The package cannot give a durable provider quote. Freeze actual caps from a dated price snapshot and a non-test calibration run.

### Primary round

```text
primary model cost =
  9 × cost(A sample)
+ 9 × cost(B sample, cap = 1.5 × projected C)
+ 9 × cost(C sample)
+ calibration and failed technical runs

primary total = model cost + primary rater compensation + storage/operations
```

Order-of-magnitude primary-round envelope for 27 scored story samples:

| Scenario | Model generation | Rater compensation | Primary-round total |
|---|---:|---:|---:|
| Low-cost/local-heavy | $25–$75 | $0–$150 | $25–$225 |
| Balanced frontier-model use | $75–$300 | $100–$300 | $175–$600 |
| Premium reasoning/many retries | $300–$900 | $150–$400 | $450–$1,300 |

The positive-control anchors are fixed synthetic evaluation samples rather than 27 additional generations. Their principal cost is authoring, pilot review, and a small amount of rating time.

### Expected MIXED path

MIXED is not a remote edge case. The calibrated operating-characteristic artifact supplies `P(MIXED)`, and the reserve round uses five new A/B/C runs:

```text
reserve samples if MIXED   = 5 runs × 3 conditions = 15
maximum scored samples     = 27 + 15 = 42
expected scored samples    = 27 + P(MIXED) × 15
expected rating cost       = primary rating cost
                           + P(MIXED) × repeat rating cost
```

At an illustrative `P(MIXED) = 0.55`, expected scored generation is 35.25 samples, roughly **1.31×** the primary-only path. A prudent pre-freeze budget should therefore carry an expected-path multiplier of about **1.3–1.5×**, depending on rater compensation and technical-abort allowance.

Illustrative expected-path planning bands:

| Scenario | Primary-only band | Expected path including likely repeat |
|---|---:|---:|
| Low-cost/local-heavy | $25–$225 | $35–$325 |
| Balanced frontier-model use | $175–$600 | $250–$900 |
| Premium reasoning/many retries | $450–$1,300 | $600–$1,900 |

These are planning envelopes, not promises. The operating-characteristic simulation itself is computationally inexpensive; additional generated samples and human ratings dominate. If calibration shows unacceptable sensitivity, compare rule calibration, rater recruitment, and sample counts explicitly. Do not quietly weaken replication, turn off `INCONCLUSIVE`, or expand non-gating diagnostics.

If the frozen calibration projects a materially higher amount, reduce non-gating diagnostics before weakening the primary gate.

## 5. Planning cost envelope — one 60–180 second film

Planning formula:

```text
film cost = story/audio calls
          + Σ(shots × attempts per approved shot × provider unit cost)
          + voice/music/SFX/licensing
          + post-production/export
          + human services
```

For a two-character, one-to-two-location microfilm using manual provider workflows:

| Scenario | Planning envelope |
|---|---:|
| Tight, low-cost providers, few retries | $100–$300 |
| Typical mixed-provider production | $300–$1,000 |
| Premium models or poor generation yield | $1,000–$3,000+ |

Generation yield dominates. Seed the first projection with the M04a spike’s attempts to first acceptable talking-character take, then replace it with observed attempts per approved shot after the first sequence. Never assume one-shot acceptance merely because the provider price is quoted per generation. A specific face, language, line, and performance may require many more attempts than a silent atmospheric shot.

## 6. Stopping points

1. **After M04a FAIL:** stop platform work and reassess the creative thesis.
2. **After M04a INCONCLUSIVE:** repair the measurement instrument before making a product claim.
3. **After M04a PASS:** complete M04b; the Story Room can then remain a standalone writing product.
4. **After M08:** one complete film can be produced without automated provider integrations.
5. **After M10:** a private production studio exists; hosted productization is optional.

## 7. Split rule

Any milestone that requires more than three migrations, two new external services, or five public interfaces must be split into sub-PRs while preserving one final milestone exit gate. M04 is already split at the product decision so work not needed for the decision cannot drift in front of it.
