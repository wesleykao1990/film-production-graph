# M03 — Typed Agent Runtime and Security Gate

Implement PydanticAI agents, fake/TestModel/FunctionModel paths, application model aliases, narrow tools, permissions, budgets, structured outputs, trusted/untrusted context framing, provenance, and the prompt-injection/authority corpus.

Agents can read/propose/report only. No approval/lock/release tool exists.

Adversarial evidence must fail to change schema, call undeclared tools, cross project scope, increase budget, reveal secrets, or approve itself.

Exit: produce a typed screenplay proposal from an approved Scene Contract using a locked repository skill, then pass the complete adversarial corpus with zero live calls.
