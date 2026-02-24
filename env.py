"""
migrations/env.py
-----------------
Alembic environment configuration for the POS + Inventory system.
Reads the database URL from the .env file (for local migration runs)
since Streamlit secrets are not available in the Alembic CLI context.

Setup steps:
  1. pip install alembic psycopg2-binary python-dotenv
  2. Create a .env file in the project root (see .env.example)
  3. alembic init migrations   (only once — already done)
  4. alembic revision --autogenerate -m "initial schema"
  5. alembic upgrade head
"""

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Load local .env so alembic CLI can find the DB URL
load_dotenv()

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect schema changes
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from database import Base  # noqa: F401
import models               # noqa: F401  registers all ORM classes

target_metadata = Base.metadata


def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable not set. "
            "Create a .env file with DATABASE_URL=postgresql://..."
        )
    return url


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL without connecting)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Online migrations (connect and apply)
# ---------------------------------------------------------------------------
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
