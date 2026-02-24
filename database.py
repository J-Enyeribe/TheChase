"""
database.py
-----------
Manages the SQLAlchemy engine and session for a Supabase (PostgreSQL) backend.
Connection credentials are loaded from Streamlit secrets (secrets.toml).
"""

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool


# ---------------------------------------------------------------------------
# Base class for all ORM models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Engine & Session Factory
# ---------------------------------------------------------------------------
def get_engine():
    """
    Build a SQLAlchemy engine from Streamlit secrets.

    Expected secrets.toml structure:
    ─────────────────────────────────
    [supabase]
    host     = "db.xxxxxxxxxxxx.supabase.co"
    port     = 5432
    database = "postgres"
    user     = "postgres"
    password  = "your-password"

    Or provide a full connection URL:
    [supabase]
    url = "postgresql://postgres:<password>@db.xxxx.supabase.co:5432/postgres"
    ─────────────────────────────────

    NullPool is used to avoid connection issues on Streamlit Community Cloud,
    where the process may be recycled between requests.
    """
    try:
        # Prefer a full URL if provided
        if "url" in st.secrets["supabase"]:
            db_url = st.secrets["supabase"]["url"]
        else:
            cfg = st.secrets["supabase"]
            db_url = (
                f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
                f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
            )
    except KeyError as e:
        raise RuntimeError(
            f"Missing Supabase secret: {e}. "
            "Check your .streamlit/secrets.toml file."
        )

    engine = create_engine(
        db_url,
        poolclass=NullPool,      # Safe for serverless / Streamlit Cloud
        echo=False,              # Set True to log SQL during development
        connect_args={
            "sslmode": "require",   # Supabase requires SSL
            "connect_timeout": 10,
        },
    )
    return engine


# ---------------------------------------------------------------------------
# Session helper — use as a context manager in your app
# ---------------------------------------------------------------------------
_engine = None
_SessionLocal = None


def get_session():
    """
    Returns a SQLAlchemy Session bound to the Supabase engine.
    Usage:
        with get_session() as session:
            results = session.query(Product).all()
    """
    global _engine, _SessionLocal

    if _engine is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """
    Create all tables in the database (safe to call multiple times).
    Typically called once on app startup.
    """
    from models import Base  # noqa: F401 — import triggers model registration
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def check_connection() -> bool:
    """Ping the database and return True if reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return False
