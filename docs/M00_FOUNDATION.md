# M00 Foundation Lite developer guide

M00 creates the production repository boundary while keeping `prototype/` as a separate behavioral reference. It intentionally contains no canonical artifact tables, workflow service, gateway, or real provider integration.

## Prerequisites

- Python 3.11 or newer and `uv`
- Node.js 22 or newer and npm
- Docker with a running daemon
- Supabase CLI 2.114.0 (the version pinned in CI)
- FFmpeg and ffprobe

No model or media-provider credentials are required.

## Commands

From the repository root:

```bash
make bootstrap
make db-reset
make lint
make typecheck
make test
```

Use `make dev` to run the API and studio together. The API defaults to `http://127.0.0.1:8000`; the studio defaults to `http://127.0.0.1:3000`.

`make db-reset` starts a database-only local Supabase stack when needed, resets migrations, applies the repeatable M00 seed, and runs database tests. Docker/Colima must be running. The remaining Supabase services are intentionally deferred until a milestone needs them.

## Production boundary

- `apps/api` and `apps/studio-web` are deployable entry points.
- `packages/domain` and `packages/contracts` are framework-independent.
- `packages/application` depends inward on ports and contracts.
- Model aliases and fake providers are local, deterministic, and non-billable.
- `infra/supabase` has one metadata-only migration proof. M01 owns substantive artifact tables.
- Ordinary pytest runs reject non-loopback network sockets.

The package validator and prototype tests run as part of the root test command. Passing the prototype alone is not M00 completion.
