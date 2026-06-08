# TruthPuzzle

TruthPuzzle is an open source multi-perspective news aggregation and analysis platform. It collects reporting about the same event from global media sources, extracts fact fragments, detects contradictions, and presents consensus, disputes, and blind spots without declaring a single official truth.

## Stack

- Backend: Python 3.11, FastAPI, SQLAlchemy async, Alembic, Celery
- Data: PostgreSQL with pgvector, Redis
- Collection: RSS via feedparser, article extraction via trafilatura, configurable scraping, Google News RSS
- AI: pluggable LLM providers through `app.services.llm.base`
- Frontend: React 18, TypeScript, Vite, Tailwind CSS
- Deployment: Docker Compose

## Quick Start

1. Copy environment values:

   ```bash
   cp .env.example .env
   ```

2. Start the full stack:

   ```bash
   docker-compose up --build
   ```

3. Open:

   - Frontend: http://localhost:3000
   - API docs: http://localhost:8000/docs

On startup the backend applies Alembic migrations and imports seed sources if the database is empty.

## Full Stack Verification

When Docker is available, run:

```bash
./scripts/verify_stack.sh
```

The script validates Compose config, starts the stack, checks `localhost:8000/health`, `localhost:8000/docs`, `localhost:3000`, verifies the `vector` extension, and confirms at least 50 seeded sources.

## Local Backend

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

## Local Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
PYTHONPATH=. python -m unittest discover tests
pip install -r requirements-dev.txt
PYTHONPATH=. pytest tests/integration -q

cd ../frontend
npm run build
npm run test:e2e
```

Performance smoke tests live in `backend/tests/performance/locustfile.py` and can be run
against a running API with:

```bash
cd backend
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

Offline evaluation entry points:

```bash
python scripts/evaluate_clustering.py path/to/clustering_labels.json
python scripts/evaluate_contradictions.py path/to/contradiction_labels.json
```

`evaluate_clustering.py` expects a JSON list with `article_id`, `gold_event_id`, and
`predicted_event_id`. `evaluate_contradictions.py` expects `{"gold": [...], "predicted": [...]}`
items keyed by `contradiction_type` and `fragment_ids`.

## Project Layout

The repository follows the structure described in `新闻聚合.md`: backend models, schemas, API routes, services, Celery tasks, frontend panels, shared data seeds, and Docker deployment files.
