"""Pytest fixtures for integration tests — DB setup and session management."""

import sqlalchemy
import sqlalchemy.orm
import pytest

import app.config as config
import app.database.models as db_models
import app.database.repository as repository


@pytest.fixture(scope="session")
def db_engine():
    """
    Create the database engine and schema once for the entire test session.

    Uses the DATABASE_URL from settings (points to the ``db`` Docker service).
    All tables are created at session start and dropped at session end.

    :return: SQLAlchemy Engine bound to the test database
    """
    engine = sqlalchemy.create_engine(config.settings.database_url)
    db_models.Base.metadata.create_all(engine)
    yield engine
    db_models.Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """
    Yield a SQLAlchemy session and truncate all tables after each test.

    Truncation (not DROP) keeps the schema intact for the next test while
    ensuring full data isolation between tests.

    :param db_engine: session-scoped SQLAlchemy engine
    :return: SQLAlchemy Session
    """
    Session = sqlalchemy.orm.sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
    with db_engine.connect() as conn:
        conn.execute(sqlalchemy.text("SET FOREIGN_KEY_CHECKS=0"))
        for table in reversed(db_models.Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.execute(sqlalchemy.text("SET FOREIGN_KEY_CHECKS=1"))
        conn.commit()


@pytest.fixture
def repo(db_session):
    """
    Provide a BookingRepository backed by the test session.

    :param db_session: per-test SQLAlchemy session
    :return: BookingRepository instance
    """
    return repository.BookingRepository(db_session)
