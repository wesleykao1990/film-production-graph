# Decisions and Open Questions — Final reviewed specification

## Accepted decisions

1. Typed Postgres artifacts are canon.
2. Agents propose; humans or explicit policy approve.
3. Locked versions are immutable.
4. Impact records are separate from lifecycle status.
5. Release A uses repository skills and `skills.lock`.
6. No durable workflow engine before M04a PASS and M04b completion.
7. Post-gate runtime is selected through ADR-001; DBOS is the default hypothesis, not a permanent mandate.
8. No model-gateway service in Release A; retain alias indirection and resolved-model provenance.
9. Prompts are immutable compiled artifacts and cannot add story facts.
10. Audio is independent of picture, with explicit canonical/native/human dialogue modes.
11. Music is sequence/scene-level; imported/licensed music is default.
12. Story quality uses a pre-registered exploratory decision heuristic whose operating characteristics—including blinded-anchor `INCONCLUSIVE` risk and the five-run MIXED repeat—must be simulated and human-reviewed before freeze; aggregate magnitude is checked against both baselines and cross-brief direction against the stronger baseline.
13. Coarse graph impact precedes path-aware semantic invalidation.
14. OTIO is editorial interchange; internal audio state remains richer.
15. Sidecar provenance and human disclosure are required release outputs; C2PA is optional when configured.
16. Deterministic and real blue-pen projects are separate.

## Decisions required before M04a final generation

- finish non-test calibration and rater pilot;
- freeze three primary briefs and an externally held reserve-brief hash commitment;
- freeze equal-information and fixed-budget baseline prompts;
- freeze Story Room and conventional budget caps from a dated price snapshot;
- target six qualified raters; freeze the five-rater recruitment fallback, seven-rater timing fallback, or three-rater full-coverage degraded mode as applicable;
- commit matched-triplet and anchor assignments, target-scene rule, randomization, positive-control anchor manifest, non-gating reliability diagnostics, shared decision code, simulator, and named operating-characteristic review;
- inspect central and sensitivity operating-characteristic tables—including anchor pass, non-degenerate `INCONCLUSIVE`, direct PASS, MIXED, repeat, and eventual-PASS behavior—and document why the trade-off is acceptable;
- decide the bounded MIXED revision owner;
- decide whether visible-dialogue feasibility is applicable to the first film.

## Decisions informed by the M04a spike and required before M06/M07

- first film language;
- visible on-camera dialogue or not;
- TTS versus human voice path;
- first ASR/lip-sync/native dialogue path;
- target editor;
- imported music source/license;
- subtitle languages;
- delivery platform/festival constraints;
- intended territories and commercial uses.

## Decisions required at M05

- choose simple runtime, DBOS, Temporal, or Restate using ADR-001 evidence;
- define runtime payload compatibility and deployment strategy.

## Deferred until M12

- hosted skill upload/registry;
- organization scopes and marketplace;
- full multi-tenancy/roles;
- executable skill sandbox;
- path-aware semantic invalidation;
- public verification service.
