"""add storage_key and storage_backend to prescriptions

Revision ID: 20260512_007
Revises: 20260511_005_add_checklist_items
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "20260512_007"
down_revision = "20260511_005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "prescriptions",
        sa.Column("storage_key", sa.String(1024), nullable=True),
    )
    op.add_column(
        "prescriptions",
        sa.Column("storage_backend", sa.String(32), nullable=True),
    )


def downgrade():
    op.drop_column("prescriptions", "storage_backend")
    op.drop_column("prescriptions", "storage_key")
