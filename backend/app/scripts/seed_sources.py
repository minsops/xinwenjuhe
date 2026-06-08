"""Import initial media source seed data if the sources table is empty."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.source import Source
from app.services.analyzer.credibility_scorer import CredibilityScorer


def find_seed_path() -> Path:
    """Find seed data from either the repository root or the Docker image layout."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "data" / "seed" / "sources.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("data/seed/sources.json was not found")


async def seed_sources() -> int:
    """Seed sources once and return number of inserted rows."""
    path = find_seed_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(Source.id).limit(1))).first()
        if existing:
            return 0
        scorer = CredibilityScorer()
        rows = []
        for item in payload:
            source = Source(**item)
            source.transparency_score = await scorer.calculate_transparency(source)
            source.composite_credibility = await scorer.compute_composite_score(source)
            rows.append(source)
        session.add_all(rows)
        await session.commit()
        return len(rows)


def main() -> None:
    inserted = asyncio.run(seed_sources())
    print(f"Seeded {inserted} sources")


if __name__ == "__main__":
    main()
