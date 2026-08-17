SHELL := /bin/sh
.DEFAULT_GOAL := help

.PHONY: help bootstrap dev db-reset lint typecheck test check

help:
	@printf '%s\n' \
	  'make bootstrap  Install locked Python and Node dependencies' \
	  'make dev        Run FastAPI and Next.js development servers' \
	  'make db-reset   Reset, seed, and test local Supabase Postgres' \
	  'make lint       Run Python and TypeScript lint checks' \
	  'make typecheck  Run Python and TypeScript type checks' \
	  'make test       Run package, prototype, API, domain, studio, and build checks' \
	  'make check      Run lint, typecheck, and test'

bootstrap:
	python3 scripts/check_environment.py
	uv sync --all-packages --all-groups --locked
	npm ci

dev:
	sh scripts/dev.sh

db-reset:
	sh scripts/db-reset.sh

lint:
	uv run ruff check apps/api/src packages tests conftest.py scripts/check_environment.py
	npm run lint

typecheck:
	uv run mypy \
	  -p film_graph.api \
	  -p film_graph.agent_runtime \
	  -p film_graph.application \
	  -p film_graph.contracts \
	  -p film_graph.domain \
	  -p film_graph.media \
	  -p film_graph.model_routing \
	  -p film_graph.provider_contracts
	uv run mypy tests/python
	npm run typecheck

test:
	uv run python scripts/validate_package.py
	uv run python -m unittest discover -s scripts/tests -v
	uv run pytest
	cd prototype && ../.venv/bin/python -m app.cli smoke
	npm test
	npm run build

check: lint typecheck test
