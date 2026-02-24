"""
database.py
-----------
Database connection for TheChase POS system.

Local dev:  reads from .env file
Streamlit Cloud: reads from .streamlit/secrets.toml
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

# Force load environment variables here to be absolutely safe
load_dotenv()

# ---------------------------------------------------------------------------
# Base class for all ORM models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Build connection URL
# ---------------------------------------------------------------------------
def _build_url() -> URL:
    """
    Builds the database URL from environment variables.
    Works for both local .env and Streamlit secrets (which are injected
    as environment variables automatically on Streamlit Cloud).
    """
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT", "5432")  # Switched default to 5432 (Session mode / Direct)
    dbname   = os.getenv("DB_NAME", "postgres")

    if not all([user, password, host]):
        raise RuntimeError(
            "Missing database credentials. "
            "Ensure DB_USER, DB_PASSWORD, DB_HOST are set in .env or Streamlit secrets."
        )

    # URL.create safely encodes special characters in passwords (e.g., @, #, ?)
    return URL.create(
        drivername="postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=dbname,
        query={"sslmode": "require"}
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def get_engine():
    return create_engine(
        _build_url(),
        poolclass=NullPool,   # required for Streamlit Cloud and Supabase Pooler
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