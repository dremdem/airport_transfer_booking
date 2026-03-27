"""Integration tests for the bookings API — full HTTP → domain → DB round-trip.

Uses a real MySQL test database brought to head via Alembic migrations.
send_notification is suppressed with a no-op for the duration of this module
so background-task writes do not leak into test assertions.
"""

import unittest.mock

import pytest


VALID_PAYLOAD = {
    "passenger_name": "Alice Smith",
    "flight_number": "BA123",
    "pickup_time": "2025-06-01T10:00:00",
    "pickup_location": "Heathrow T2",
    "dropoff_location": "City Hotel",
}


@pytest.fixture(autouse=True)
def suppress_send_notification():
    """
    Replace send_notification with a no-op for every test in this module.

    The background task opens its own session and commits independently, which
    would write notification_log rows that are visible to later assertions under
    READ COMMITTED.  Suppressing it keeps each test focused on booking behaviour.

    autouse=True scopes this to the module — it does not affect other integration
    test modules that need send_notification to run for real.

    :return: None
    """
    with unittest.mock.patch("app.integration.notifications.send_notification"):
        yield


class TestBookingsAPI:
    """Full HTTP → domain → DB integration tests for the /bookings routes."""

    def test_create_booking_returns_201(self, client):
        """
        POST /bookings with valid data persists the booking and returns 201 with
        pending status and all expected fields.

        :return: None
        """
        response = client.post("/bookings", json=VALID_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["passenger_name"] == VALID_PAYLOAD["passenger_name"]
        assert data["flight_number"] == VALID_PAYLOAD["flight_number"]
        assert "id" in data

    def test_get_booking_by_id(self, client):
        """
        GET /bookings/{id} returns the persisted booking with correct data.

        :return: None
        """
        created = client.post("/bookings", json=VALID_PAYLOAD).json()
        response = client.get(f"/bookings/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["passenger_name"] == VALID_PAYLOAD["passenger_name"]

    def test_pending_to_confirmed(self, client):
        """
        PATCH /bookings/{id}/status transitions a pending booking to confirmed.

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        response = client.patch(f"/bookings/{booking_id}/status", json={"status": "confirmed"})
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_confirmed_to_completed(self, client):
        """
        PATCH /bookings/{id}/status transitions a confirmed booking to completed.

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        client.patch(f"/bookings/{booking_id}/status", json={"status": "confirmed"})
        response = client.patch(f"/bookings/{booking_id}/status", json={"status": "completed"})
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_pending_to_cancelled(self, client):
        """
        PATCH /bookings/{id}/status cancels a pending booking directly.

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        response = client.patch(f"/bookings/{booking_id}/status", json={"status": "cancelled"})
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_invalid_transition_returns_422(self, client):
        """
        PATCH /bookings/{id}/status returns 422 for a disallowed transition
        (completed → pending).

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        client.patch(f"/bookings/{booking_id}/status", json={"status": "confirmed"})
        client.patch(f"/bookings/{booking_id}/status", json={"status": "completed"})
        response = client.patch(f"/bookings/{booking_id}/status", json={"status": "pending"})
        assert response.status_code == 422

    def test_get_nonexistent_booking_returns_404(self, client):
        """
        GET /bookings/{id} returns 404 when the booking does not exist.

        :return: None
        """
        response = client.get("/bookings/999999")
        assert response.status_code == 404

    def test_list_bookings_by_date(self, client):
        """
        GET /bookings?date=YYYY-MM-DD returns only bookings whose pickup_time
        falls on that date.

        :return: None
        """
        client.post("/bookings", json=VALID_PAYLOAD)
        response = client.get("/bookings", params={"date": "2025-06-01"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) >= 1
        assert all(r["pickup_time"].startswith("2025-06-01") for r in results)
