#!/usr/bin/env sh
set -eu

uv run uvicorn film_graph.api.main:app --host 127.0.0.1 --port 8000 --reload &
api_pid=$!
npm run dev:studio &
studio_pid=$!

cleanup() {
  kill "$api_pid" "$studio_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait "$api_pid" "$studio_pid"

