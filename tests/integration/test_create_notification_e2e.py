"""End-to-end test: POST /bookings → background task → notification_log row.

Verifies the full wiring from the HTTP route through FastAPI BackgroundTasks
into send_notification and the database — without mocking any layer.
"""

import unittest.mock

import fastapi.testclient
import sqlalchemy.orm

import app.api.dependencies as dependencies
import app.database.models as db_models
import app.main as main_app


VALID_PAYLOAD = {
    "passenger_name": "Alice Smith",
    "flight_number": "BA123",
    "pickup_time": "2025-06-01T10:00:00",
    "pickup_location": "Heathrow T2",
    "dropoff_location": "City Hotel",
}


def _query_notification(db_engine, booking_id):
    """
    Open a fresh session to read notification rows committed by send_notification.

    send_notification commits via its own session so a new session is required
    to see the rows outside its transaction boundary.

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


class TestCreateBookingNotificationE2E:
    """End-to-end test for the POST /bookings → send_notification pipeline."""

    def test_notification_log_row_written_after_create(self, db_session, db_engine):
        """
        POST /bookings enqueues send_notification as a BackgroundTask; FastAPI's
        TestClient runs background tasks synchronously, so the notification_log
        row is committed before the response is received.

        This test does not mock send_notification — it exercises the full wiring
        from route → BackgroundTasks → send_notification → DB.

        :param db_session: per-test SQLAlchemy session from the root conftest
        :param db_engine: session-scoped test engine from the root conftest
        :return: None
        """
        def override_get_db():
            """
            FastAPI dependency override that yields the test session.

            :return: generator yielding the test db_session
            """
            yield db_session

        test_factory = sqlalchemy.orm.sessionmaker(bind=db_engine)
        main_app.app.dependency_overrides[dependencies.get_db] = override_get_db
        try:
            with unittest.mock.patch("app.database.session.SessionLocal", test_factory):
                with fastapi.testclient.TestClient(main_app.app) as client:
                    response = client.post("/bookings", json=VALID_PAYLOAD)
        finally:
            main_app.app.dependency_overrides.clear()

        assert response.status_code == 201
        booking_id = response.json()["id"]
        rows = _query_notification(db_engine, booking_id)
        assert len(rows) == 1
        assert rows[0].event_type == "booking_created"
