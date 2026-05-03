"""
alembic/env.py
Alembic migration environment — supports both offline (SQL script) and
online (live DB connection) modes.

Reads DATABASE_URL from the app's Settings so the same .env drives
both the app and migrations.
"""
import sys
import os
from logging.config import fileConfig
from pathlib import Path

# Make sure the backend/app package is importable when running alembic from
# the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Load Alembic ini config ───────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Pull DATABASE_URL from pydantic Settings ──────────────────────────────────
from app.config import settings

# Override sqlalchemy.url so alembic.ini can leave it blank / as a placeholder.
config.set_main_option("sqlalchemy.url", str(settings.database_url))

# ── Import all models so Alembic can detect schema changes ───────────────────
# Every model module must be imported here; otherwise autogenerate won't see it.
from app.models.base import Base          # noqa: F401  — must come first
from app.models.user import User          # noqa: F401
from app.models.patient import Patient    # noqa: F401
from app.models.prescription import Prescription   # noqa: F401
from app.models.discrepancy_report import DiscrepancyReport  # noqa: F401

target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Outputs SQL to stdout — useful for DBAs who need to review SQL before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,            # detect column type changes
        compare_server_default=True,  # detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ───────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations with a live DB connection (default when using `alembic upgrade`).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # one-shot connection; no pooling during migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entrypoint ────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()