"""Shared pytest fixtures for the Transfer Booking Service test suite."""

import alembic.command
import alembic.config
import pytest
import sqlalchemy
import sqlalchemy.orm

import app.config as config
import app.database.models as db_models


@pytest.fixture(scope="session")
def db_engine():
    """
    Apply all Alembic migrations once for the entire test session, then yield
    the engine.  Shared by integration and API tests so migrations run exactly
    once regardless of which test modules are collected.

    All tables are removed via ``downgrade base`` at session teardown.

    :return: SQLAlchemy Engine bound to the test database
    """
    alembic_cfg = alembic.config.Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", config.settings.test_database_url)
    alembic.command.upgrade(alembic_cfg, "head")
    engine = sqlalchemy.create_engine(config.settings.test_database_url)
    yield engine
    engine.dispose()
    alembic.command.downgrade(alembic_cfg, "base")


@pytest.fixture
def db_session(db_engine):
    """
    Yield a SQLAlchemy session and delete all rows after each test.

    Row deletion keeps the schema intact while ensuring full data isolation
    between tests.

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
