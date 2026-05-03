"""
Add completeness_score + missing_fields to prescriptions
and extend discrepancylabel enum with lowercase variants.

Revision ID: 210cd32e6256
Revises: 004_add_gin_indexes
Create Date: 2026-05-01 20:45:00.000000 UTC
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------
# Alembic identifiers
# ---------------------------------------------------------
revision: str = "210cd32e6256"
down_revision: Union[str, None] = "004_add_gin_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------
def upgrade() -> None:
    conn = op.get_bind()

    # ---------------------------------------------------------
    # 1. CHECK EXISTING COLUMNS (FIXED FOR SQLAlchemy 2.0)
    # ---------------------------------------------------------
    result = conn.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'prescriptions'
    """))

    existing_columns = {row[0] for row in result}

    # ---------------------------------------------------------
    # 2. ADD NEW COLUMNS SAFELY
    # ---------------------------------------------------------
    if "completeness_score" not in existing_columns:
        op.add_column(
            "prescriptions",
            sa.Column("completeness_score", sa.Float(), nullable=True)
        )

    if "missing_fields" not in existing_columns:
        op.add_column(
            "prescriptions",
            sa.Column("missing_fields", postgresql.JSONB(), nullable=True)
        )

    # ---------------------------------------------------------
    # 3. EXTEND ENUM SAFELY (LOWERCASE VALUES)
    # ---------------------------------------------------------
    enum_values = [
        "no discrepancy",
        "omission",
        "commission",
        "inconsistency",
        "illegibility"
    ]

    for val in enum_values:
        op.execute(sa.text(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = '{val}'
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'discrepancylabel'
                )
            ) THEN
                ALTER TYPE discrepancylabel ADD VALUE '{val}';
            END IF;
        END$$;
        """))


# ---------------------------------------------------------
# DOWNGRADE
# ---------------------------------------------------------
def downgrade() -> None:
    # Remove added columns
    op.drop_column("prescriptions", "missing_fields")
    op.drop_column("prescriptions", "completeness_score")

    # ⚠️ NOTE:
    # PostgreSQL does NOT support removing enum values safely.
    # So we intentionally DO NOT remove lowercase enum values.