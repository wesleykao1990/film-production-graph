# Studio UX and Lineage — Final reviewed specification

## 1. Two UI stages

### M04a Minimum Review and Rating Studio

Build only what the story experiment needs:

- project/brief selector;
- artifact editor and schema-aware form;
- version history/diff;
- approve/reject/lock actions;
- premise/candidate comparison;
- bounded subtext-patch review;
- matched-triplet blind rating with workload timer;
- rater assignment, blinded-anchor, and instrument-validity status;
- forced-choice anchor controls with no tie radio button; a separate **Report technical problem** action aborts/replaces a defective task outside the scored dataset;
- PASS/MIXED/FAIL/INCONCLUSIVE decision report.

No React Flow canvas is required.

### M04b Story Room completion UI

After PASS, add only the forms and views required for sequence/setup-payoff review, deferred screenplay passes, and Fountain export. Do not build the full lineage canvas here.

### M10 Full Production Studio

Add after audio, shot, provider, and timeline domains stabilize:

- filtered lineage canvas;
- impact visualization;
- approval inbox;
- workflow monitor;
- skill/run inspector;
- generation comparison;
- audio and editing timeline;
- release/provenance dashboard.

## 2. Artifact inspector

Show:

- canonical payload;
- schema/version/status;
- parent/diff;
- actor/time/hash;
- approvals/findings;
- rights/delivery relevance;
- incoming/outgoing edges;
- impact records and bulk actions;
- run/skill/provider provenance.

## 3. Impact UX

Avoid a wall of stale warnings. Default views distinguish:

```text
contradicted             high priority
rederive requested       action pending
possibly impacted        collapsed/informational
reviewed valid            hidden by default
```

Bulk actions:

- acknowledge and keep prior snapshot;
- run validators;
- rederive selected subtree;
- compare old/new upstream;
- show actual contradictions only.

## 4. Lineage graph

Node families:

```text
evidence/story/sequence/scene/shot/audio
prompt/generation/select/edit/release
skill/run/decision/rights/delivery/cost
```

Default graph loads a selected neighborhood rather than the entire project.

## 5. Audio and native-dialogue review

For a shot, show:

- declared dialogue source;
- locked text;
- transcript diff for native dialogue;
- Voice Profile/performance;
- native component candidates;
- human promotion/rejection;
- music sequence cue and ambience continuity.

## 6. Release UX

Checklist displays:

- Delivery Specification pass/fail;
- rights status;
- subtitle languages;
- rejected/unapproved timeline assets;
- provenance manifest status;
- human AI disclosure;
- optional C2PA status;
- actual/projected cost.

## 7. Accessibility

Approval, rating, diff, and release workflows must be keyboard operable, screen-reader labeled, and not rely solely on color.
