"""Pytest fixtures for API endpoint tests."""

import unittest.mock

import fastapi.testclient
import pytest

import app.api.dependencies as dependencies
import app.main as main_app


@pytest.fixture(autouse=True)
def mock_send_notification():
    """
    Patch ``send_notification`` for every API test to prevent real side-effects.

    Yields the mock so individual tests can assert on call arguments when needed.

    :return: unittest.mock.MagicMock replacing send_notification
    """
    with unittest.mock.patch(
        "app.integration.notifications.send_notification"
    ) as mock:
        yield mock


@pytest.fixture
def client(db_session):
    """
    Provide a FastAPI TestClient with the ``get_db`` dependency overridden to
    use the per-test database session.

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
