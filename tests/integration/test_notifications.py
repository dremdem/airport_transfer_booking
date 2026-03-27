"""Integration tests for the send_notification background task."""

import unittest.mock

import pytest
import sqlalchemy.orm

import app.database.models as db_models
import app.database.repository as repository
import app.domain.enums as enums
import app.domain.models as domain_models
import app.integration.notifications as notifications
import datetime


@pytest.fixture(autouse=True)
def patch_session_local(db_engine):
    """
    Redirect send_notification's internal SessionLocal to the test engine so
    its writes land in transfer_bookings_test, not the live transfer_bookings.

    autouse=True applies this to every test in the module automatically.

    :param db_engine: session-scoped test engine from the root conftest
    :return: None
    """
    test_factory = sqlalchemy.orm.sessionmaker(bind=db_engine)
    with unittest.mock.patch("app.database.session.SessionLocal", test_factory):
        yield


BOOKING_CREATE = domain_models.BookingCreate(
    passenger_name="Alice Smith",
    flight_number="BA123",
    pickup_time=datetime.datetime(2025, 6, 1, 10, 0),
    pickup_location="Heathrow T2",
    dropoff_location="City Hotel",
    status=enums.BookingStatus.PENDING,
)


def _query_notification(db_engine, booking_id):
    """
    Open a fresh session to read notification rows committed by send_notification.

    send_notification commits via its own session.  The test's db_session runs
    under REPEATABLE READ and cannot see those rows — a new session is required.

    :param db_engine: SQLAlchemy engine for the test database
    :param booking_id: booking id to filter on
    :return: list of NotificationLogORM rows
    """
    Session = sqlalchemy.orm.sessionmaker(bind=db_engine)
    with Session() as fresh:
        return (
            fresh.query(db_models.NotificationLogORM)
            .filter_by(booking_id=booking_id)
            .all()
        )


class TestSendNotification:
    """Tests for notifications.send_notification."""

    def test_inserts_notification_log_row(self, db_session, db_engine):
        """
        send_notification writes a notification_log row for the given booking id.

        :return: None
        """
        booking = repository.BookingRepository(db_session).create(BOOKING_CREATE)
        notifications.send_notification(booking.id)
        assert len(_query_notification(db_engine, booking.id)) == 1

    def test_sets_event_type_booking_created(self, db_session, db_engine):
        """
        The notification row carries event_type='booking_created'.

        :return: None
        """
        booking = repository.BookingRepository(db_session).create(BOOKING_CREATE)
        notifications.send_notification(booking.id)
        row = _query_notification(db_engine, booking.id)[0]
        assert row.event_type == "booking_created"

    def test_message_references_booking_id(self, db_session, db_engine):
        """
        The notification message contains the booking id.

        :return: None
        """
        booking = repository.BookingRepository(db_session).create(BOOKING_CREATE)
        notifications.send_notification(booking.id)
        row = _query_notification(db_engine, booking.id)[0]
        assert str(booking.id) in row.message

    def test_uses_own_session(self, db_session):
        """
        send_notification accepts only a booking_id — no session argument.
        Verifies the function signature is correct for background task use.

        :return: None
        """
        booking = repository.BookingRepository(db_session).create(BOOKING_CREATE)
        notifications.send_notification(booking.id)
