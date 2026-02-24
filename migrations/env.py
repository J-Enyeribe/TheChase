"""
migrations/env.py
-----------------
Alembic migration environment for TheChase POS system.
Reads credentials from .env file in the project root.
"""

import os
import sys
import pathlib
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

# ── Alembic config ───────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Add project root to path so models/database can be imported ──────────────
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from db.database import Base  # noqa: F401

target_metadata = Base.metadata


def get_url() -> str:
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT", "6543")
    dbname   = os.getenv("DB_NAME", "postgres")

    if not all([user, password, host]):
        raise RuntimeError(
            "Missing database credentials in .env file.\n"
            "Ensure these are set:\n"
            "  DB_USER=postgres.sgjizzyhqjejncdodafe\n"
            "  DB_PASSWORD=your_password\n"
            "  DB_HOST=aws-1-eu-west-1.pooler.supabase.com\n"
            "  DB_PORT=6543\n"
            "  DB_NAME=postgres\n"
        )

    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{host}:{port}/{dbname}"
        f"?sslmode=require"
    )


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"sslmode": "require"},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
