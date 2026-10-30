"""Add signal record idempotency constraint with full data grain dimensions.

Revision ID: 002_signal_record_idempotency
Revises: 001_initial_schema
Create Date: 2026-10-30 23:45:00
"""

from __future__ import annotations

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_signal_record_idempotency"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely handle existing database state:
    # 1. If an existing constraint exists with the old 5-column grain, replace it with the full grain.
    # 2. Add the unique constraint with NULLS NOT DISTINCT on:
    #    (tenant_id, source_id, metric_code, period_start, geography_id, workplace_id, record_version)
    op.execute("""
    DO $$
    DECLARE
        cols text;
    BEGIN
        SELECT pg_get_constraintdef(oid) INTO cols
        FROM pg_constraint
        WHERE conname = 'uq_signal_records_idempotency'
          AND conrelid = 'signal_records'::regclass;

        IF cols IS NOT NULL AND cols NOT LIKE '%geography_id%' THEN
            -- Drop the narrower legacy constraint
            ALTER TABLE signal_records DROP CONSTRAINT uq_signal_records_idempotency;
            cols := NULL;
        END IF;

        IF cols IS NULL THEN
            ALTER TABLE signal_records
            ADD CONSTRAINT uq_signal_records_idempotency
            UNIQUE NULLS NOT DISTINCT (
                tenant_id, source_id, metric_code, period_start,
                geography_id, workplace_id, record_version
            );
        END IF;
    END
    $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE signal_records DROP CONSTRAINT IF EXISTS uq_signal_records_idempotency;")
