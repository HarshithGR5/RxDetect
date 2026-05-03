"""Add GIN indexes on JSONB columns for fast prescription field queries

Revision ID: 004_add_gin_indexes
Revises: 003_add_token_denylist
Create Date: 2025-01-04 00:00:00.000000 UTC
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_add_gin_indexes"
down_revision: Union[str, None] = "003_add_token_denylist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # GIN index allows fast @> (contains) queries on extracted_fields JSONB
    # e.g. SELECT * FROM prescriptions WHERE extracted_fields @> '{"diagnosis": "diabetes"}'
    op.execute(
        "CREATE INDEX ix_prescriptions_extracted_fields_gin "
        "ON prescriptions USING GIN (extracted_fields)"
    )
    op.execute(
        "CREATE INDEX ix_discrepancy_reports_rules_triggered_gin "
        "ON discrepancy_reports USING GIN (rules_triggered)"
    )
    op.execute(
        "CREATE INDEX ix_discrepancy_reports_evidence_sources_gin "
        "ON discrepancy_reports USING GIN (evidence_sources)"
    )

    # Partial index: only non-deleted prescriptions (most queries filter deleted_at IS NULL)
    op.execute(
        "CREATE INDEX ix_prescriptions_active "
        "ON prescriptions (uploaded_by, created_at DESC) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_prescriptions_active")
    op.execute("DROP INDEX IF EXISTS ix_discrepancy_reports_evidence_sources_gin")
    op.execute("DROP INDEX IF EXISTS ix_discrepancy_reports_rules_triggered_gin")
    op.execute("DROP INDEX IF EXISTS ix_prescriptions_extracted_fields_gin")