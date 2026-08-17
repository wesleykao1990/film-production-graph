# M00 — Foundation Lite

Create a reproducible production monorepo and local development environment. First run the package validator and `prototype/` tests; preserve the prototype as a behavioral reference but do not port its SQLite/static/mock implementation.

Build Next.js/TypeScript studio scaffold, FastAPI/Python API, pure domain/contracts packages, Supabase local config/migration/seed, PydanticAI test dependencies, application model aliases, fake providers, FFmpeg/ffprobe checks, commands, network guard, CI, and ADRs.

Do not add Temporal, DBOS, Restate, workflow server, LiteLLM service, real providers, or substantive artifact tables.

Tests: reference prototype remains green; clean bootstrap; db reset/seed; API/studio smoke; domain import boundary; FFmpeg checks; lint/typecheck; unexpected egress fails; full tests pass without credentials.

Exit: prove clean clone → bootstrap → db reset → full test.
