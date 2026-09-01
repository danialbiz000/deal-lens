"""SQLAlchemy engine/session setup.

SQLite for local Phase 0 dev, Postgres-portable by construction (see
docs/phase0-vertical-slice-design.md section 2): String(36) UUID PKs,
Numeric (not Float) for money/ratio columns, no SQLite-only pragmas relied
upon anywhere in application code. Switching to Postgres later is meant to
be a one-line DATABASE_URL change, nothing more.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables from the ORM models.

    db/schema.sql is the canonical, hand-maintained Postgres-portable DDL
    reference (design doc section 2); this function is the local-dev
    convenience path so `apps/api` boots against a fresh SQLite file with a
    single command, per the README's fresh-clone walkthrough. The two must
    be kept in agreement -- there is no migrations tool in this slice
    (alembic was called out as optional in the design doc and is not needed
    yet for a single-file SQLite dev DB).
    """
    from app.models import (  # noqa: F401
        assumption,
        company,
        financial_period,
        ic_simulation,
        lbo_case,
        memo,
        peer,
        scenario,
    )

    Base.metadata.create_all(bind=engine)
