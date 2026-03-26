"""Pytest fixtures specific to integration tests."""

import pytest

import app.database.repository as repository


@pytest.fixture
def repo(db_session):
    """
    Provide a BookingRepository backed by the test session.

    :param db_session: per-test SQLAlchemy session from the root conftest
    :return: BookingRepository instance
    """
    return repository.BookingRepository(db_session)
