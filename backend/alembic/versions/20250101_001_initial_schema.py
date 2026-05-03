"""Initial schema: users, patients, prescriptions, discrepancy_reports

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-01-01 00:00:00.000000 UTC
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("pharmacist", "admin", "viewer", name="userrole"),
            nullable=False,
            server_default="pharmacist",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── patients ──────────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mrn", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(16), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("known_allergies", sa.Text(), nullable=True),
        sa.Column("current_medications", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_patients_mrn", "patients", ["mrn"], unique=True)

    # ── prescriptions ─────────────────────────────────────────────────────
    op.create_table(
        "prescriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("local_path", sa.String(512), nullable=True),
        sa.Column("input_type", sa.String(64), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded", "processing", "ocr_done", "validated", "analyzed", "failed",
                name="prescriptionstatus",
            ),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("celery_job_id", sa.String(128), nullable=True),
        sa.Column("raw_ocr_text", sa.Text(), nullable=True),
        sa.Column("extracted_fields", postgresql.JSONB(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("drug_validation_result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_prescriptions_uploaded_by", "prescriptions", ["uploaded_by"])
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"])
    op.create_index("ix_prescriptions_status", "prescriptions", ["status"])

    # ── discrepancy_reports ───────────────────────────────────────────────
    op.create_table(
        "discrepancy_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "prescription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prescriptions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "label",
            sa.Enum(
                "No Discrepancy", "Omission", "Commission", "Inconsistency", "Illegibility",
                name="discrepancylabel",
            ),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rules_triggered", postgresql.JSONB(), nullable=True),
        sa.Column("rule_label", sa.String(64), nullable=True),
        sa.Column("llm_label", sa.String(64), nullable=True),
        sa.Column("llm_confidence", sa.Float(), nullable=True),
        sa.Column("llm_reason", sa.Text(), nullable=True),
        sa.Column("evidence_sources", postgresql.JSONB(), nullable=True),
        sa.Column("ml_label", sa.String(64), nullable=True),
        sa.Column("ml_confidence", sa.Float(), nullable=True),
        sa.Column("ml_features", postgresql.JSONB(), nullable=True),
        sa.Column("consensus", sa.String(8), nullable=True),
        sa.Column("pdf_local_path", sa.String(512), nullable=True),
        sa.Column("pdf_generated_at", sa.DateTime(), nullable=True),
        sa.Column("pharmacist_label", sa.String(64), nullable=True),
        sa.Column("feedback_note", sa.Text(), nullable=True),
        sa.Column("feedback_at", sa.DateTime(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_discrepancy_reports_prescription_id",
        "discrepancy_reports",
        ["prescription_id"],
        unique=True,
    )
    op.create_index("ix_discrepancy_reports_label", "discrepancy_reports", ["label"])


def downgrade() -> None:
    op.drop_table("discrepancy_reports")
    op.drop_index("ix_prescriptions_status", "prescriptions")
    op.drop_index("ix_prescriptions_patient_id", "prescriptions")
    op.drop_index("ix_prescriptions_uploaded_by", "prescriptions")
    op.drop_table("prescriptions")
    op.drop_index("ix_patients_mrn", "patients")
    op.drop_table("patients")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")

    # Drop custom enum types
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS prescriptionstatus")
    op.execute("DROP TYPE IF EXISTS discrepancylabel")