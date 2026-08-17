# Declarative Workflows

This directory contains reviewed, non-executable workflow plans. The production workflow compiler validates allowed step types and produces an immutable normalized plan.

- `dialogue-development.workflow.yaml` is the full target example.
- `prototype-subtext-review.workflow.yaml` is the reduced plan executed by the local deterministic prototype.

Adding a YAML file does not grant shell, filesystem, network, or approval authority. Step execution remains controlled by the application runtime and skill permissions.
