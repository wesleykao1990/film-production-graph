# Existing Repository Assessment Prompt — Final v3.0

Assess the existing repository against Film Production Graph Final v3.0 before changing code.

Read `START_HERE.md`, `PRD.md`, `IMPLEMENTATION_PLAN.md`, `AGENTS.md`, `prototype/README.md`, and `docs/ARCHITECTURE.md`. Run the prototype tests, but treat the prototype as a behavioral reference rather than a migration target.

Return:

1. current stack and package boundaries;
2. existing database/migration/auth/storage/model/media/workflow systems;
3. which Final v3.0 milestones are complete, partial, absent, or conflicting;
4. any premature infrastructure such as a workflow cluster, gateway service, hosted skill registry, or full graph UI;
5. migration risks to immutable artifacts, separate impact records, repository skill locks, rights/delivery/audio contracts, and M4 evaluation;
6. the smallest non-destructive path to the earliest incomplete milestone;
7. tests required before modification.

Do not rewrite working subsystems solely to match package names. Do not remove an existing durable runtime without evidence. Create an ADR for keep/replace decisions. Implement no code until the assessment is written, then implement only the explicitly assigned milestone.
