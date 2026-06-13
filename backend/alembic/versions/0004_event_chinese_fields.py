"""Persist Chinese event display fields.

Revision ID: 0004_event_chinese_fields
Revises: 0003_source_scraper_verified_at
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_event_chinese_fields"
down_revision = "0003_source_scraper_verified_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("title_zh", sa.String(500), nullable=True))
    op.add_column("events", sa.Column("summary_zh", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "summary_zh")
    op.drop_column("events", "title_zh")
