"""Integration tests for multi-step booking flows — full HTTP → domain → DB round-trip.

Responsibility boundary
-----------------------
tests/api/test_bookings.py  — HTTP contract: status codes, response shape,
                              input validation, exception mapping, notification
                              enqueue.  No duplicate happy-path flows here.

tests/integration/test_bookings_api.py (this file) — end-to-end flows that
                              span multiple state transitions and prove the
                              full stack (route → service → repository → MySQL)
                              works correctly for scenarios not covered by the
                              API suite.

send_notification is suppressed with a module-scoped autouse fixture so
notification_log writes do not interfere with booking assertions.
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

    autouse=True scopes this to the module only — it does not affect other
    integration test modules that need send_notification to run for real.

    :return: None
    """
    with unittest.mock.patch("app.integration.notifications.send_notification"):
        yield


class TestBookingsAPI:
    """End-to-end booking flows that span multiple state transitions."""

    def test_full_booking_lifecycle(self, client):
        """
        A booking can be created and immediately retrieved with correct data.

        Anchors the full DB wiring: route → service → repository → MySQL → response.
        Complements the HTTP-contract tests in tests/api/ by verifying the
        persisted state, not just the response shape.

        :return: None
        """
        response = client.post("/bookings", json=VALID_PAYLOAD)
        assert response.status_code == 201
        booking_id = response.json()["id"]

        get_response = client.get(f"/bookings/{booking_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == booking_id
        assert get_response.json()["status"] == "pending"

    def test_confirmed_to_completed(self, client):
        """
        A booking can transition pending → confirmed → completed across two
        separate PATCH requests, with the final state persisted correctly.

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        client.patch(f"/bookings/{booking_id}/status", json={"status": "confirmed"})
        response = client.patch(f"/bookings/{booking_id}/status", json={"status": "completed"})
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_pending_to_cancelled(self, client):
        """
        A booking can be cancelled directly from pending in a single transition.

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        response = client.patch(f"/bookings/{booking_id}/status", json={"status": "cancelled"})
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
