from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# SQLite needs check_same_thread disabled because FastAPI runs sync handlers in
# a threadpool. The arg is harmless to omit for other backends (e.g. Azure SQL).
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


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
