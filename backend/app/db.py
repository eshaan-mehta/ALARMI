from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_is_sqlite = settings.database_url.startswith("sqlite")

# SQLite needs check_same_thread disabled because FastAPI runs sync handlers in
# a threadpool. The arg is harmless to omit for other backends (e.g. Azure SQL).
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# pool_pre_ping matters for Azure SQL serverless: the DB auto-pauses when idle,
# so a pooled connection can be dead by the next request. Pre-ping discards it
# and reconnects (the paused DB resumes) instead of erroring. No-op for SQLite.
engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=not _is_sqlite,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


if _is_sqlite:
    # SQLite ignores foreign keys unless this pragma is set per connection.
    # Enable it so FK/orphan behaviour matches a real DB (e.g. Azure SQL) —
    # otherwise local and cloud disagree on what data is valid.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist. Stand-in for real migrations (Alembic)
    until the schema stabilises."""
    # Import every domain's models so they register on Base before create_all.
    from .designs import models as _designs  # noqa: F401
    from .modules import models as _modules  # noqa: F401
    from .projects import models as _projects  # noqa: F401

    Base.metadata.create_all(bind=engine)
