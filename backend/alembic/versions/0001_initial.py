"""Initial TruthPuzzle schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200)),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("feed_type", sa.String(20), nullable=False),
        sa.Column("feed_url", sa.Text()),
        sa.Column("scraper_config", sa.JSON()),
        sa.Column("mbfc_bias", sa.String(30)),
        sa.Column("mbfc_factual", sa.String(30)),
        sa.Column("mbfc_score", sa.SmallInteger()),
        sa.Column("rsf_country_rank", sa.SmallInteger()),
        sa.Column("transparency_score", sa.SmallInteger()),
        sa.Column("composite_credibility", sa.SmallInteger()),
        sa.Column("ownership_info", sa.Text()),
        sa.Column("funding_info", sa.Text()),
        sa.Column("has_correction_policy", sa.Boolean(), server_default=sa.false()),
        sa.Column("separates_news_opinion", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("last_collected_at", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_sources_region", "sources", ["region"])
    op.create_index("idx_sources_language", "sources", ["language"])

    op.create_table(
        "discovered_sources",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("domain", sa.String(255), nullable=False, unique=True),
        sa.Column("language", sa.String(10)),
        sa.Column("region_hint", sa.String(50)),
        sa.Column("status", sa.String(30), server_default="pending_review"),
        sa.Column("sample_urls", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_discovered_sources_status", "discovered_sources", ["status"])

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("title_en", sa.String(500)),
        sa.Column("summary", sa.Text()),
        sa.Column("category", sa.String(50)),
        sa.Column("region_primary", sa.String(50)),
        sa.Column("regions_involved", sa.ARRAY(sa.String(200))),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("article_count", sa.Integer(), server_default="0"),
        sa.Column("source_count", sa.Integer(), server_default="0"),
        sa.Column("language_count", sa.Integer(), server_default="0"),
        sa.Column("region_count", sa.Integer(), server_default="0"),
        sa.Column("heat_score", sa.Float(), server_default="0"),
        sa.Column("first_reported_at", sa.DateTime(timezone=True)),
        sa.Column("last_updated_at", sa.DateTime(timezone=True)),
        sa.Column("center_embedding", Vector(384)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_events_status", "events", ["status"])
    op.create_index("idx_events_heat", "events", ["heat_score"])
    op.execute(
        "CREATE INDEX idx_events_center_embedding ON events "
        "USING ivfflat (center_embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=False, unique=True),
        sa.Column("title_original", sa.Text(), nullable=False),
        sa.Column("title_translated", sa.Text()),
        sa.Column("content_original", sa.Text(), nullable=False),
        sa.Column("content_translated", sa.Text()),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("author", sa.String(200)),
        sa.Column("image_url", sa.Text()),
        sa.Column("embedding", Vector(384)),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id")),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_articles_source", "articles", ["source_id"])
    op.create_index("idx_articles_event", "articles", ["event_id"])
    op.create_index("idx_articles_published", "articles", [sa.text("published_at DESC")])
    op.execute(
        "CREATE INDEX idx_articles_embedding ON articles "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "fact_fragments",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("article_id", sa.Uuid(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("fragment_type", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_en", sa.Text()),
        sa.Column("entities", sa.JSON()),
        sa.Column("numbers", sa.JSON()),
        sa.Column("source_attribution", sa.String(50)),
        sa.Column("certainty_level", sa.String(20)),
        sa.Column("timestamp_mentioned", sa.DateTime(timezone=True)),
        sa.Column("embedding", Vector(384)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_facts_event", "fact_fragments", ["event_id"])
    op.create_index("idx_facts_type", "fact_fragments", ["fragment_type"])
    op.execute(
        "CREATE INDEX idx_facts_embedding ON fact_fragments "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "contradictions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("contradiction_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(10), server_default="medium"),
        sa.Column("fragment_ids", sa.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("source_ids", sa.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_contradictions_event", "contradictions", ["event_id"])
    op.create_index("idx_contradictions_type", "contradictions", ["contradiction_type"])

    op.create_table(
        "event_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id"), nullable=False, unique=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("consensus_facts", sa.JSON(), nullable=False),
        sa.Column("disputed_facts", sa.JSON(), nullable=False),
        sa.Column("blind_spots", sa.JSON(), nullable=False),
        sa.Column("narrative_frames", sa.JSON(), nullable=False),
        sa.Column("source_graph", sa.JSON()),
        sa.Column("timeline", sa.JSON()),
        sa.Column("analysis_version", sa.Integer(), server_default="1"),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("article_count_at_analysis", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("event_analyses")
    op.drop_index("idx_contradictions_type", table_name="contradictions")
    op.drop_index("idx_contradictions_event", table_name="contradictions")
    op.drop_table("contradictions")
    op.execute("DROP INDEX IF EXISTS idx_facts_embedding")
    op.drop_index("idx_facts_type", table_name="fact_fragments")
    op.drop_index("idx_facts_event", table_name="fact_fragments")
    op.drop_table("fact_fragments")
    op.execute("DROP INDEX IF EXISTS idx_articles_embedding")
    op.drop_index("idx_articles_published", table_name="articles")
    op.drop_index("idx_articles_event", table_name="articles")
    op.drop_index("idx_articles_source", table_name="articles")
    op.drop_table("articles")
    op.execute("DROP INDEX IF EXISTS idx_events_center_embedding")
    op.drop_index("idx_events_heat", table_name="events")
    op.drop_index("idx_events_status", table_name="events")
    op.drop_table("events")
    op.drop_index("idx_sources_language", table_name="sources")
    op.drop_index("idx_sources_region", table_name="sources")
    op.drop_index("idx_discovered_sources_status", table_name="discovered_sources")
    op.drop_table("discovered_sources")
    op.drop_table("sources")
