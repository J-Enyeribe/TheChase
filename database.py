"""
database.py
-----------
Database connection for TheChase POS system.

Local dev:  reads from .env file
Streamlit Cloud: reads from .streamlit/secrets.toml
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool


# ---------------------------------------------------------------------------
# Base class for all ORM models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Build connection URL
# ---------------------------------------------------------------------------
def _build_url() -> str:
    """
    Builds the database URL from environment variables.
    Works for both local .env and Streamlit secrets (which are injected
    as environment variables automatically on Streamlit Cloud).
    """
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT", "6543")
    dbname   = os.getenv("DB_NAME", "postgres")

    if not all([user, password, host]):
        raise RuntimeError(
            "Missing database credentials. "
            "Ensure DB_USER, DB_PASSWORD, DB_HOST are set in .env or Streamlit secrets."
        )

    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{host}:{port}/{dbname}"
        f"?sslmode=require"
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def get_engine():
    return create_engine(
        _build_url(),
        poolclass=NullPool,   # required for Streamlit Cloud
        echo=False,
    )


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
def get_session():
    """
    Use as a context manager:
        with get_session() as session:
            session.query(Product).all()
    """
    engine = get_engine()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
def check_connection() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
