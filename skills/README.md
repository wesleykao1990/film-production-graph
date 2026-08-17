# Repository Skills

Release A loads reviewed instruction skills from this directory and pins every regular file through `skills.lock`.

The included `subtext-pass` demonstrates the package format:

```text
subtext-pass/
  SKILL.md
  skill.yaml
  references/
  schemas/
  tests/
```

Add methods by creating another directory with the same structure. Portable instructions and routing description belong in `SKILL.md`; application permissions, contracts, budgets, resources, and stage belong in `skill.yaml`.

The runtime must never execute arbitrary uploaded Python or shell code. The production M03 agent reads these reviewed packages through application-owned tools and records the exact content hash in provenance.
