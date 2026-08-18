# ADR-011 — M04a protected-generation preflight

## Status

Accepted for the pre-credential M04a checkpoint.

## Decision

Keep the ordinary M03 runtime fake-only. Add a separate, provider-neutral M04a
preflight that verifies a pinned protocol and its referenced experiment inputs,
requires one explicit model identity and positive per-condition budgets, declares a
provenance destination, and compiles the calibration or primary request matrix.

Dry-run mode never reads a credential. Protected execution preflight checks a
credential only after all non-secret controls pass. Neither mode invokes a provider.
Primary execution preflight additionally requires the protocol to be frozen, the
calibration-derived Story Room and conventional caps to match the declared execution
budgets, the conventional multiplier to equal exactly `1.5`, every materialized
per-condition budget to match the execution plan, and the reviewed
operating-characteristics artifact to be hash-pinned.

## Consequences

- Ordinary tests remain deterministic, offline, and non-billable.
- A credential value cannot enter an immutable request plan, report, exception, or
  committed experiment template.
- A caller cannot pair an altered in-memory protocol mapping with a different pinned
  YAML file.
- The plan records every verified source pin needed for later provenance.
- Provider selection and a provider-specific protected adapter remain explicit work;
  adding a key alone cannot silently enable network access.
- Calibration, human pilot/review, protocol freeze, primary generation, ratings, and
  the final product decision remain protected human/evaluation work.
