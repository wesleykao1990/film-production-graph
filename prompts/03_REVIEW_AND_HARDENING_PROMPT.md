# Independent Review and Hardening Prompt — Final v3.0

Review the pull request for **[MILESTONE]** as an independent senior engineer/security reviewer.

Compare implementation with `AGENTS.md`, the milestone prompt, schemas, and exit gate. Inspect actual code and tests; do not rely on the PR summary.

Prioritize:

- canon/immutability/authority violations;
- lifecycle versus impact conflation;
- prompt-injection or skill-permission gaps;
- rights/delivery/provenance bypasses;
- unbounded cost or external calls;
- provider leakage into core contracts;
- audio-policy inconsistencies;
- fake tests that do not prove the claimed exit gate;
- premature later-milestone infrastructure;
- compatibility/migration risk;
- for M04a specifically: analyzer/simulator rule drift, unreviewed operating characteristics, silent changes to assignment replication, or a MIXED repeat that is harder than the primary gate.

Return findings by severity with file/line evidence and minimal fixes. Implement only agreed fixes within the same milestone and rerun the exit gate. Do not add features from later milestones.
