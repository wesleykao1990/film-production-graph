# Milestone Prompt Template

Implement **[MILESTONE ID — TITLE] only**.

## Required reading

- `AGENTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- relevant architecture/spec/schema/example files
- this milestone prompt

## Precondition

State and verify the prior exit gate. For M04b, verify M04a is PASS. For M05+, verify M04b is complete after M04a PASS. For M12, verify hosted productization is an explicit decision.

## Work

1. Inspect current code and public contracts.
2. Write the smallest implementation sequence.
3. Add tests and failure paths.
4. Implement without starting later milestones.
5. Run the exit demonstration.
6. Report behavior, files, migrations/contracts, commands/results, security/rights/cost/compatibility implications, risks, and next dependencies.

## Prohibited

- live provider calls in ordinary tests;
- agent approval capability;
- mutation of locked canon;
- unreviewed skill code execution;
- provider fields in core contracts;
- scope expansion beyond the exit gate.
