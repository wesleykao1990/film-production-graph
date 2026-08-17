#!/usr/bin/env sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the local Supabase database." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but its daemon is not running." >&2
  exit 1
fi

if ! command -v supabase >/dev/null 2>&1; then
  echo "Supabase CLI is required. See docs/M00_FOUNDATION.md." >&2
  exit 1
fi

SUPABASE_DB_ONLY_EXCLUDES="gotrue,realtime,storage-api,imgproxy,kong,mailpit,postgrest,postgres-meta,studio,edge-runtime,logflare,vector,supavisor"

if ! supabase status --workdir infra >/dev/null 2>&1; then
  supabase start --workdir infra --exclude "$SUPABASE_DB_ONLY_EXCLUDES"
fi

supabase db reset --local --workdir infra
supabase test db --workdir infra
