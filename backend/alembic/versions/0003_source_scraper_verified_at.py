"""Track scraper selector verification timestamps.

Revision ID: 0003_source_scraper_verified_at
Revises: 0002_event_center_pgvector
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_source_scraper_verified_at"
down_revision = "0002_event_center_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("scraper_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "scraper_verified_at")
