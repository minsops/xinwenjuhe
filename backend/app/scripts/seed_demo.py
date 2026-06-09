"""Seed a demo event with articles and analysis for local trial usage."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select

from app.db import AsyncSessionLocal
from app.models.article import Article
from app.models.credibility import EventAnalysis
from app.models.event import Event
from app.models.source import Source


DEMO_TITLE = "Cross-border incident draws conflicting casualty reports"
DEMO_SOURCE_ALIASES = {
    "Reuters": ("Reuters",),
    "Al Jazeera": ("Al Jazeera", "半岛电视台"),
    "IRNA": ("IRNA", "Islamic Republic News Agency"),
}


async def seed_demo() -> dict:
    """Insert demo event data once and return inserted or existing counts."""
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Event).where(Event.title == DEMO_TITLE))
        if existing:
            sources = await _demo_sources(session)
            updated = await _sync_demo_articles(session, existing.id, sources)
            article_count = await session.scalar(
                select(func.count()).select_from(Article).where(Article.event_id == existing.id)
            )
            await session.commit()
            return {"status": "updated" if updated else "exists", "event_id": str(existing.id), "articles": article_count or 0}

        sources = await _demo_sources(session)
        now = datetime.now(timezone.utc)
        event = Event(
            title=DEMO_TITLE,
            title_en=DEMO_TITLE,
            summary="Multiple outlets report the same incident while disagreeing on numbers and attribution.",
            category="conflict",
            region_primary="middle_east",
            regions_involved=["middle_east", "europe", "north_america"],
            status="active",
            article_count=3,
            source_count=3,
            language_count=2,
            region_count=3,
            heat_score=82.0,
            first_reported_at=now - timedelta(hours=8),
            last_updated_at=now - timedelta(hours=1),
            center_embedding=[0.1] * 384,
        )
        session.add(event)
        await session.flush()

        articles = _demo_articles(sources, event.id, now)
        session.add_all(articles)
        await session.flush()

        analysis = EventAnalysis(
            event_id=event.id,
            summary=(
                "Available reports agree that an overnight border incident occurred and emergency crews responded. "
                "Sources differ on casualty figures and responsibility claims, with independent verification still limited."
            ),
            consensus_facts=[
                {
                    "fact": "An overnight incident occurred and local authorities responded.",
                    "confirmed_by": 3,
                    "total": 3,
                    "source_ids": [str(source.id) for source in sources.values()],
                    "article_ids": [str(article.id) for article in articles[:2]],
                }
            ],
            disputed_facts=[
                {
                    "topic": "Casualty count differs between 12 and more than 200.",
                    "type": "number_discrepancy",
                    "severity": "critical",
                    "details": {
                        "values": [
                            {"source": "Reuters", "value": 12},
                            {"source": "IRNA", "value": 200},
                        ]
                    },
                },
                {
                    "topic": "Sources disagree over who was responsible for the incident.",
                    "type": "attribution_conflict",
                    "severity": "high",
                },
            ],
            blind_spots=[
                {
                    "description": "Independent on-site verification is absent from most reports.",
                    "mentioned_by": 1,
                    "total": 3,
                }
            ],
            narrative_frames=[
                {"source_id": str(sources["Reuters"].id), "frames": ["official uncertainty"], "tone": "neutral"},
                {"source_id": str(sources["Al Jazeera"].id), "frames": ["regional dispute"], "tone": "neutral"},
                {"source_id": str(sources["IRNA"].id), "frames": ["attack attribution"], "tone": "hostile"},
            ],
            source_graph={
                "nodes": [
                    {"id": str(source.id), "type": "source"}
                    for source in sources.values()
                ],
                "edges": [
                    {"from": str(article.source_id), "to": str(article.id), "type": "reported"}
                    for article in articles
                ],
            },
            timeline=[
                {
                    "timestamp": articles[0].published_at.isoformat(),
                    "fact": "Initial reports described an overnight incident.",
                    "fragment_type": "what",
                    "article_id": str(articles[0].id),
                    "source_id": str(articles[0].source_id),
                },
                {
                    "timestamp": articles[2].published_at.isoformat(),
                    "fact": "Later reports issued a higher casualty claim.",
                    "fragment_type": "number",
                    "article_id": str(articles[2].id),
                    "source_id": str(articles[2].source_id),
                },
            ],
            article_count_at_analysis=3,
        )
        session.add(analysis)
        await session.commit()
        return {"status": "seeded", "event_id": str(event.id), "articles": len(articles)}


def _demo_articles(sources: dict[str, Source], event_id, now: datetime) -> list[Article]:
    return [
        Article(
            source_id=sources["Reuters"].id,
            event_id=event_id,
            external_url="https://demo.truthpuzzle.local/reuters/overnight-strike",
            title_original="Officials report 12 casualties after overnight strike",
            content_original=(
                "An overnight incident occurred near a contested border area shortly before dawn, according to local officials and emergency responders. "
                "Authorities said rescue teams reached the area after residents reported blasts and visible smoke from several nearby roads.\n\n"
                "Officials reported 12 casualties in their initial statement and said the number could change as hospitals and local authorities completed their checks. "
                "The same statement said investigators had not yet confirmed whether the incident was caused by an airstrike, artillery fire, or an accidental explosion.\n\n"
                "A security official who was not authorized to speak publicly said access to the site remained limited. "
                "Reuters could not independently verify the casualty figure, the exact location of the blast, or claims about who was responsible."
            ),
            language="en",
            author="TruthPuzzle demo desk",
            published_at=now - timedelta(hours=7, minutes=30),
            embedding=[0.1] * 384,
        ),
        Article(
            source_id=sources["Al Jazeera"].id,
            event_id=event_id,
            external_url="https://demo.truthpuzzle.local/aljazeera/border-incident",
            title_original="Regional officials dispute responsibility for border incident",
            content_original=(
                "Local authorities confirmed that an overnight incident took place near the border, but officials from neighboring administrations offered conflicting accounts of what happened. "
                "One side said the blast followed military activity in the area, while another said the incident was being used to justify a broader political accusation.\n\n"
                "Residents described hearing explosions before sunrise and seeing emergency vehicles move through roads leading toward the affected district. "
                "Several witnesses said phone networks were unreliable for part of the morning, making it difficult to confirm the scale of the damage.\n\n"
                "Regional officials disputed who was responsible and said independent verification was still limited. "
                "Humanitarian workers contacted by the outlet said they were seeking access to the site before making public casualty estimates."
            ),
            language="en",
            author="TruthPuzzle demo desk",
            published_at=now - timedelta(hours=5),
            embedding=[0.1] * 384,
        ),
        Article(
            source_id=sources["IRNA"].id,
            event_id=event_id,
            external_url="https://demo.truthpuzzle.local/irna/casualty-claim",
            title_original="Officials claim more than 200 affected in overnight attack",
            content_original=(
                "Officials described the incident as an attack and claimed more than 200 people were affected, citing preliminary reports from local administrators and medical staff. "
                "The report said several families had left the area after the incident and that emergency response teams were still compiling figures.\n\n"
                "The article attributed responsibility to foreign-backed actors and said the incident showed a pattern of pressure on communities near the border. "
                "It did not publish independent documentation for the casualty figure, and other outlets used more cautious wording when describing the scale of the incident.\n\n"
                "Independent monitors had not verified the higher casualty claim by the time of publication. "
                "Officials said a fuller report would be released after investigators reviewed hospital records, field reports, and statements from local authorities."
            ),
            language="en",
            author="TruthPuzzle demo desk",
            published_at=now - timedelta(hours=3),
            embedding=[0.1] * 384,
        ),
    ]


async def _sync_demo_articles(session, event_id, sources: dict[str, Source]) -> int:
    now = datetime.now(timezone.utc)
    demo_articles = _demo_articles(sources, event_id, now)
    demo_urls = [article.external_url for article in demo_articles]
    rows = (
        await session.execute(
            select(Article).where(
                Article.event_id == event_id,
                Article.external_url.in_(demo_urls),
            )
        )
    ).scalars().all()
    by_url = {article.external_url: article for article in rows}
    updated = 0
    for article in demo_articles:
        existing = by_url.get(article.external_url)
        if existing:
            existing.title_original = article.title_original
            existing.content_original = article.content_original
            existing.author = article.author
            existing.language = article.language
            updated += 1
        else:
            session.add(article)
            updated += 1
    extras = (
        await session.execute(
            select(Article).where(Article.event_id == event_id, ~Article.external_url.in_(demo_urls))
        )
    ).scalars().all()
    for article in extras:
        article.event_id = None
        updated += 1
    event = await session.get(Event, event_id)
    if event:
        event.article_count = 3
        event.source_count = 3
        event.language_count = 2
        event.region_count = 3
        event.heat_score = 82.0
        event.regions_involved = ["middle_east", "europe", "north_america"]
        event.first_reported_at = now - timedelta(hours=8)
        event.last_updated_at = now - timedelta(hours=1)
    return updated


async def _demo_sources(session) -> dict[str, Source]:
    names = tuple({alias for aliases in DEMO_SOURCE_ALIASES.values() for alias in aliases})
    rows = (
        await session.execute(
            select(Source)
            .where(or_(Source.name.in_(names), Source.name_en.in_(names)))
        )
    ).scalars().all()
    by_key = {}
    for key, aliases in DEMO_SOURCE_ALIASES.items():
        by_key[key] = next(
            (
                source
                for source in rows
                if source.name in aliases or source.name_en in aliases
            ),
            None,
        )
    missing = [key for key, source in by_key.items() if source is None]
    if missing:
        raise RuntimeError(f"Missing seed sources: {', '.join(missing)}")
    return by_key


def main() -> None:
    print(asyncio.run(seed_demo()))


if __name__ == "__main__":
    main()
