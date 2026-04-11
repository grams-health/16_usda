import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

_engine = None
_SessionFactory = None


def init_db(url: str = None):
    """Initialize the shared database engine and session factory."""
    global _engine, _SessionFactory
    if url is None:
        url = os.environ.get("DATABASE_URL", "sqlite:///usda_integration.db")
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(url)
    _SessionFactory = sessionmaker(bind=_engine)


def get_engine():
    """Return the shared engine."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session():
    """Create and return a new session."""
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionFactory()


def reset():
    """Tear down the shared engine and session factory."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None
