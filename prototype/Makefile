.PHONY: install dev test reset smoke

install:
	python -m pip install -e ".[dev]"

dev:
	python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	python -m pytest

reset:
	python -m app.cli reset

smoke:
	python -m app.cli smoke
