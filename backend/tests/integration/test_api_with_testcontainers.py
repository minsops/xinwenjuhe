"""Integration smoke tests for FastAPI endpoints against a real Postgres database."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

try:
    import pytest
except ImportError as exc:
    raise unittest.SkipTest("pytest is not installed") from exc

pytest.importorskip("alembic")
pytest.importorskip("asyncpg")
pytest.importorskip("httpx")
pytest.importorskip("testcontainers")

from alembic import command
from alembic.config import Config
import httpx
from testcontainers.postgres import PostgresContainer


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _asyncpg_url(container: PostgresContainer) -> str:
    host = container.get_container_host_ip()
    port = container.get_exposed_port(5432)
    username = container.username
    password = container.password
    database = container.dbname
    return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"


@pytest.fixture(scope="module")
def migrated_database_url() -> str:
    """Start pgvector Postgres and apply the real Alembic migration."""
    try:
        container = PostgresContainer("pgvector/pgvector:pg16")
        container.start()
    except Exception as exc:
        pytest.skip(f"Docker testcontainer is not available: {exc}")

    database_url = _asyncpg_url(container)
    monkeypatch = pytest.MonkeyPatch()
    original_cwd = Path.cwd()
    monkeypatch.setenv("DATABASE_URL", database_url)
    os.chdir(BACKEND_ROOT)

    from app.config import get_settings

    get_settings.cache_clear()
    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(alembic_cfg, "head")

    yield database_url

    os.chdir(original_cwd)
    monkeypatch.undo()
    container.stop()


@pytest.mark.asyncio
async def test_sources_endpoint_reads_rows_from_migrated_database(migrated_database_url: str) -> None:
    """Verify API routing, migration DDL, and async DB sessions work together."""
    from app.db import AsyncSessionLocal, engine
    from app.main import create_app
    from app.models.source import Source

    async with AsyncSessionLocal() as session:
        session.add(
            Source(
                name="Integration Wire",
                name_en="Integration Wire",
                country="Testland",
                region="integration",
                language="en",
                feed_type="rss",
                feed_url="https://example.test/rss.xml",
            )
        )
        await session.commit()

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/sources", params={"region": "integration"})

    await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["name"] == "Integration Wire"
