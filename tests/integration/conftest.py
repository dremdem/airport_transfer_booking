"""Pytest fixtures for integration tests — DB setup and session management."""

import sqlalchemy
import sqlalchemy.orm
import alembic.config
import alembic.command
import pytest

import app.config as config
import app.database.models as db_models
import app.database.repository as repository


@pytest.fixture(scope="session")
def db_engine():
    """
    Apply all Alembic migrations to bring the test DB to ``head``, then yield
    the engine.  Using Alembic (rather than ``Base.metadata.create_all``) means
    the integration tests exercise the actual migration, catching any drift
    between the ORM model and the revision before it reaches production.

    All tables are removed via ``downgrade base`` at session teardown.

    :return: SQLAlchemy Engine bound to the test database
    """
    alembic_cfg = alembic.config.Config("alembic.ini")
    alembic.command.upgrade(alembic_cfg, "head")
    engine = sqlalchemy.create_engine(config.settings.database_url)
    yield engine
    engine.dispose()
    alembic.command.downgrade(alembic_cfg, "base")


@pytest.fixture
def db_session(db_engine):
    """
    Yield a SQLAlchemy session and delete all rows after each test.

    Row deletion (not DROP) keeps the schema intact for the next test while
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
