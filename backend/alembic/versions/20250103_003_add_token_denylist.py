"""Add token_denylist for server-side JWT logout/revocation

Revision ID: 003_add_token_denylist
Revises: 002_add_audit_log
Create Date: 2025-01-03 00:00:00.000000 UTC
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_add_token_denylist"
down_revision: Union[str, None] = "002_add_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "token_denylist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("jti", sa.String(255), nullable=False),          # JWT ID claim
        sa.Column("token_type", sa.String(16), nullable=False),    # "access" | "refresh"
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),    # original JWT exp — row can be purged after this
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_token_denylist_jti", "token_denylist", ["jti"], unique=True)
    op.create_index("ix_token_denylist_user_id", "token_denylist", ["user_id"])
    op.create_index("ix_token_denylist_expires_at", "token_denylist", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_token_denylist_expires_at", "token_denylist")
    op.drop_index("ix_token_denylist_user_id", "token_denylist")
    op.drop_index("ix_token_denylist_jti", "token_denylist")
    op.drop_table("token_denylist")