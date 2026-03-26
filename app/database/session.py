"""Database engine and session factory for the airport transfer booking service."""

import collections.abc

import sqlalchemy
import sqlalchemy.orm

import app.config as config


engine = sqlalchemy.create_engine(config.settings.database_url)

SessionLocal = sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> collections.abc.Generator[sqlalchemy.orm.Session, None, None]:
    """
    FastAPI dependency that yields a database session and closes it on exit.

    Designed for use with ``Depends(get_db)`` in route handlers. The session
    is closed in the ``finally`` block to ensure cleanup even on exceptions.

    :return: generator yielding a SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
