"""add checklist_items to discrepancy_reports

Revision ID: 20260511_005
Revises: 20260501_210cd32e6256
Create Date: 2026-05-11

Adds:
- discrepancy_reports.checklist_items (JSONB) — 27-parameter clinical audit results
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260511_005"
down_revision = "210cd32e6256"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add checklist_items column to discrepancy_reports
    op.add_column(
        "discrepancy_reports",
        sa.Column("checklist_items", JSONB, nullable=True),
    )

    # Also ensure prescription.extracted_fields schema can store new fields
    # (existing JSONB column — no migration needed, schema-less)

    # Create a GIN index on checklist_items for JSONB query performance
    op.create_index(
        "ix_discrepancy_reports_checklist_items_gin",
        "discrepancy_reports",
        ["checklist_items"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_discrepancy_reports_checklist_items_gin",
        table_name="discrepancy_reports",
    )
    op.drop_column("discrepancy_reports", "checklist_items")