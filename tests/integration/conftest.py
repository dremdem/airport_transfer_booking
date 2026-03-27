"""Pytest fixtures specific to integration tests."""

import fastapi.testclient
import pytest

import app.api.dependencies as dependencies
import app.database.repository as repository
import app.main as main_app


@pytest.fixture
def repo(db_session):
    """
    Provide a BookingRepository backed by the test session.

    :param db_session: per-test SQLAlchemy session from the root conftest
    :return: BookingRepository instance
    """
    return repository.BookingRepository(db_session)


@pytest.fixture
def client(db_session):
    """
    Provide a FastAPI TestClient with the ``get_db`` dependency overridden to
    use the per-test database session.

    Does not suppress send_notification — tests that need a no-op must apply
    their own patch (e.g. test_bookings_api.py uses a file-scoped autouse fixture).

    :param db_session: per-test SQLAlchemy session from the root conftest
    :return: fastapi.testclient.TestClient bound to the test app
    """
    def override_get_db():
        """
        FastAPI dependency override that yields the test session.

        :return: generator yielding the test db_session
        """
        yield db_session

    main_app.app.dependency_overrides[dependencies.get_db] = override_get_db
    with fastapi.testclient.TestClient(main_app.app) as c:
        yield c
    main_app.app.dependency_overrides.clear()
