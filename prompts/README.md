# Coding-Agent Prompt Guide — Final v3.0

- `00_INITIATING_PROMPT.md`: greenfield repository; implements M00 Foundation Lite only.
- `01_EXISTING_REPOSITORY_PROMPT.md`: maps an existing codebase before changes.
- `02_MILESTONE_PROMPT_TEMPLATE.md`: reusable scoped ticket.
- `03_REVIEW_AND_HARDENING_PROMPT.md`: independent audit of one milestone.
- `milestones/`: M00–M12 prompts, with M04 split into M04a/M04b in revised execution order.

Cadence:

1. Run one milestone prompt.
2. Review exit evidence.
3. Run the hardening prompt with a separate agent/model.
4. Fix blockers/high findings.
5. Merge.
6. Start the next milestone only when its precondition is satisfied.

M04a is a hard product gate. Its shared decision rule must pass pre-freeze operating-characteristic review before final generation. M04b/M05+ must not begin after FAIL or INCONCLUSIVE. M12 hosted-registry work is intentionally last.
