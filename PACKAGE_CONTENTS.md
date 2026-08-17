# Package Contents — Final v3.0.0

## Requested deliverables

| Deliverable | Path |
|---|---|
| Product Requirements Document | `PRD.md` |
| Implementation plan | `IMPLEMENTATION_PLAN.md` |
| Runnable prototype | `prototype/` |
| Initial coding-agent prompt | `INITIAL_PROMPT.md` |

## Supporting material

- `START_HERE.md` — build and verification sequence.
- `AGENTS.md` — repository-wide coding-agent contract.
- `FINAL_REVIEW_STATUS.md` — concise review outcome without full review-history duplication.
- `docs/` — architecture, domain, audio, workflows, security, tests, UX, rights, provider strategy, and M04 protocol.
- `prompts/milestones/` — one prompt for every milestone/sub-milestone.
- `skills/` — directly installable repository skill example.
- `workflows/` — declarative workflow examples.
- `schemas/` — typed JSON Schema contracts.
- `examples/golden/blue-pen-fixture/` — deterministic CI fixture.
- `examples/golden/blue-pen-film/` — real-production skeleton.
- `examples/evals/story-room-gate/` — M04 calibration, assignment, rating, and analysis fixtures.
- `scripts/` — package validator and executable M04 analysis/simulation.
- `templates/` — ADR, milestone, skill, provider, human-review, and dialogue-feasibility templates.
- `machine-readable/` — artifact type, milestone, release, and package manifests.

## Prototype files

```text
prototype/
├── README.md
├── pyproject.toml
├── requirements.txt
├── Makefile
├── app/
│   ├── main.py
│   ├── repository.py
│   ├── skills.py
│   ├── workflows.py
│   ├── services.py
│   ├── agent.py
│   ├── db.py
│   ├── seed.py
│   ├── cli.py
│   └── static/
├── data/seed_project.json
└── tests/
```

The prototype tests canonical versioning, impact propagation, human approval, skill hashing, workflow pausing, untrusted-text authority boundaries, reset behavior, and static/API availability.
