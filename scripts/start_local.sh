#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-truthpuzzle}"
export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-0}"

if ! docker info >/dev/null 2>&1; then
  if command -v open >/dev/null 2>&1; then
    open -a Docker >/dev/null 2>&1 || true
  fi
  printf "Waiting for Docker"
  for _ in $(seq 1 90); do
    if docker info >/dev/null 2>&1; then
      printf "\n"
      break
    fi
    printf "."
    sleep 2
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Open Docker Desktop, then run this script again." >&2
  exit 1
fi

docker compose up -d db redis meilisearch backend frontend

for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1 && curl -fsS http://localhost:3000/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

docker compose exec -T backend python -m app.scripts.seed_demo >/dev/null

echo "TruthPuzzle is ready:"
echo "  http://127.0.0.1:3000/"
