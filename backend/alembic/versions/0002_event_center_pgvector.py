"""Store event center embeddings as pgvector.

Revision ID: 0002_event_center_pgvector
Revises: 0001_initial
Create Date: 2026-06-02
"""

from __future__ import annotations

from alembic import op

revision = "0002_event_center_pgvector"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'events'
                  AND column_name = 'center_embedding'
                  AND udt_name <> 'vector'
            ) THEN
                ALTER TABLE events
                ALTER COLUMN center_embedding TYPE vector(384)
                USING CASE
                    WHEN center_embedding IS NULL THEN NULL
                    ELSE center_embedding::vector(384)
                END;
            END IF;
        END $$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_center_embedding ON events "
        "USING ivfflat (center_embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_events_center_embedding")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'events'
                  AND column_name = 'center_embedding'
                  AND udt_name = 'vector'
            ) THEN
                ALTER TABLE events
                ALTER COLUMN center_embedding TYPE double precision[]
                USING CASE
                    WHEN center_embedding IS NULL THEN NULL
                    ELSE vector_to_float4(center_embedding, 384, false)::double precision[]
                END;
            END IF;
        END $$;
        """
    )
