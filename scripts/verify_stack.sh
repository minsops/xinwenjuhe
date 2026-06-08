#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to verify the full stack" >&2
  exit 127
fi

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-truthpuzzle}"
export COMPOSE_BAKE="${COMPOSE_BAKE:-false}"
export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-0}"

compose_cmd=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
fi

"${compose_cmd[@]}" config >/dev/null
"${compose_cmd[@]}" up --build -d

cleanup() {
  "${compose_cmd[@]}" logs --tail=100 backend celery_worker celery_beat frontend || true
}
trap cleanup ERR

for _ in $(seq 1 60); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS http://localhost:8000/health >/dev/null
curl -fsS http://localhost:8000/docs >/dev/null

for _ in $(seq 1 60); do
  if curl -fsS http://localhost:3000 >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

for _ in $(seq 1 60); do
  if curl -fsS http://localhost:7700/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS http://localhost:3000 >/dev/null
curl -fsS http://localhost:7700/health >/dev/null

"${compose_cmd[@]}" exec -T backend python -m app.scripts.seed_sources >/dev/null
"${compose_cmd[@]}" exec -T backend python - <<'PY'
import asyncio
from sqlalchemy import text
from app.db import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        vector = await session.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        source_count = await session.scalar(text("SELECT count(*) FROM sources"))
        assert vector == "vector"
        assert source_count >= 50

asyncio.run(main())
PY

echo "TruthPuzzle stack verification passed"
