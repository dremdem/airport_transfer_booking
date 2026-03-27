"""API endpoint tests for the /bookings routes."""

VALID_PAYLOAD = {
    "passenger_name": "Alice Smith",
    "flight_number": "BA123",
    "pickup_time": "2025-06-01T10:00:00",
    "pickup_location": "Heathrow T2",
    "dropoff_location": "City Hotel",
}


class TestCreateBooking:
    """Tests for POST /bookings."""

    def test_returns_201(self, client):
        """
        Creating a booking with valid data returns HTTP 201.

        :return: None
        """
        response = client.post("/bookings", json=VALID_PAYLOAD)
        assert response.status_code == 201

    def test_response_contains_all_fields(self, client):
        """
        Response body includes id, all input fields, status, and timestamps.

        :return: None
        """
        response = client.post("/bookings", json=VALID_PAYLOAD)
        data = response.json()
        assert data["passenger_name"] == "Alice Smith"
        assert data["flight_number"] == "BA123"
        assert data["pickup_location"] == "Heathrow T2"
        assert data["dropoff_location"] == "City Hotel"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_new_booking_status_is_pending(self, client):
        """
        Newly created bookings always have status ``pending``.

        :return: None
        """
        response = client.post("/bookings", json=VALID_PAYLOAD)
        assert response.json()["status"] == "pending"

    def test_notification_enqueued(self, client, mock_send_notification):
        """
        A background notification is dispatched with the new booking id.

        :return: None
        """
        response = client.post("/bookings", json=VALID_PAYLOAD)
        booking_id = response.json()["id"]
        mock_send_notification.assert_called_once_with(booking_id)


class TestCreateBookingValidation:
    """Input-validation tests for POST /bookings."""

    def test_empty_passenger_name_returns_422(self, client):
        """
        An empty passenger_name string is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "passenger_name": ""})
        assert response.status_code == 422

    def test_passenger_name_exceeds_max_length_returns_422(self, client):
        """
        passenger_name longer than 255 characters is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "passenger_name": "A" * 256})
        assert response.status_code == 422

    def test_empty_flight_number_returns_422(self, client):
        """
        An empty flight_number string is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "flight_number": ""})
        assert response.status_code == 422

    def test_flight_number_exceeds_max_length_returns_422(self, client):
        """
        flight_number longer than 20 characters is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "flight_number": "A" * 21})
        assert response.status_code == 422

    def test_empty_pickup_location_returns_422(self, client):
        """
        An empty pickup_location string is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "pickup_location": ""})
        assert response.status_code == 422

    def test_pickup_location_exceeds_max_length_returns_422(self, client):
        """
        pickup_location longer than 500 characters is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "pickup_location": "A" * 501})
        assert response.status_code == 422

    def test_empty_dropoff_location_returns_422(self, client):
        """
        An empty dropoff_location string is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "dropoff_location": ""})
        assert response.status_code == 422

    def test_dropoff_location_exceeds_max_length_returns_422(self, client):
        """
        dropoff_location longer than 500 characters is rejected with HTTP 422.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "dropoff_location": "A" * 501})
        assert response.status_code == 422

    def test_extra_field_returns_422(self, client):
        """
        Unexpected fields in the request body are rejected with HTTP 422.

        Prevents callers from smuggling in forbidden fields like ``status``.

        :return: None
        """
        response = client.post("/bookings", json={**VALID_PAYLOAD, "status": "confirmed"})
        assert response.status_code == 422


class TestGetBooking:
    """Tests for GET /bookings/{id}."""

    def test_returns_200_for_existing_booking(self, client):
        """
        GET on an existing booking id returns HTTP 200 with booking data.

        :return: None
        """
        created = client.post("/bookings", json=VALID_PAYLOAD).json()
        response = client.get(f"/bookings/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_returns_404_for_missing_booking(self, client):
        """
        GET on a non-existent id returns HTTP 404.

        :return: None
        """
        response = client.get("/bookings/999999")
        assert response.status_code == 404


class TestUpdateBookingStatus:
    """Tests for PATCH /bookings/{id}/status."""

    def test_valid_transition_returns_200(self, client):
        """
        A permitted status transition returns HTTP 200 with updated booking.

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        response = client.patch(
            f"/bookings/{booking_id}/status",
            json={"status": "confirmed"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_invalid_transition_returns_422(self, client):
        """
        A disallowed status transition returns HTTP 422.

        :return: None
        """
        booking_id = client.post("/bookings", json=VALID_PAYLOAD).json()["id"]
        response = client.patch(
            f"/bookings/{booking_id}/status",
            json={"status": "completed"},
        )
        assert response.status_code == 422

    def test_missing_booking_returns_404(self, client):
        """
        PATCH on a non-existent booking id returns HTTP 404.

        :return: None
        """
        response = client.patch(
            "/bookings/999999/status",
            json={"status": "confirmed"},
        )
        assert response.status_code == 404


class TestListBookingsByDate:
    """Tests for GET /bookings?date=YYYY-MM-DD."""

    def test_returns_bookings_on_given_date(self, client):
        """
        Bookings whose pickup_time falls on the requested date are returned.

        :return: None
        """
        client.post("/bookings", json=VALID_PAYLOAD)
        response = client.get("/bookings", params={"date": "2025-06-01"})
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_returns_empty_list_for_date_with_no_bookings(self, client):
        """
        A date with no bookings returns an empty list, not a 404.

        :return: None
        """
        response = client.get("/bookings", params={"date": "2099-01-01"})
        assert response.status_code == 200
        assert response.json() == []

    def test_missing_date_param_returns_422(self, client):
        """
        Omitting the required ``date`` query parameter returns HTTP 422.

        :return: None
        """
        response = client.get("/bookings")
        assert response.status_code == 422


class TestGetBookingTimeline:
    """Tests for GET /bookings/{id}/timeline."""

    def test_returns_empty_list_for_booking_with_no_transitions(self, client):
        """
        A booking that has never had its status changed returns an empty timeline.

        :return: None
        """
        create_resp = client.post("/bookings", json=VALID_PAYLOAD)
        booking_id = create_resp.json()["id"]
        response = client.get(f"/bookings/{booking_id}/timeline")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_one_entry_after_status_transition(self, client):
        """
        One timeline entry is returned after a single status transition.

        :return: None
        """
        create_resp = client.post("/bookings", json=VALID_PAYLOAD)
        booking_id = create_resp.json()["id"]
        client.patch(f"/bookings/{booking_id}/status", json={"status": "confirmed"})
        response = client.get(f"/bookings/{booking_id}/timeline")
        assert response.status_code == 200
        entries = response.json()
        assert len(entries) == 1
        assert entries[0]["old_status"] == "pending"
        assert entries[0]["new_status"] == "confirmed"

    def test_entry_contains_booking_fields(self, client):
        """
        Each timeline entry includes the booking's current details.

        :return: None
        """
        create_resp = client.post("/bookings", json=VALID_PAYLOAD)
        booking_id = create_resp.json()["id"]
        client.patch(f"/bookings/{booking_id}/status", json={"status": "confirmed"})
        response = client.get(f"/bookings/{booking_id}/timeline")
        assert response.status_code == 200
        entry = response.json()[0]
        assert entry["booking_id"] == booking_id
        assert entry["passenger_name"] == VALID_PAYLOAD["passenger_name"]
        assert entry["flight_number"] == VALID_PAYLOAD["flight_number"]
        assert entry["pickup_location"] == VALID_PAYLOAD["pickup_location"]
        assert entry["dropoff_location"] == VALID_PAYLOAD["dropoff_location"]

    def test_entries_ordered_chronologically(self, client):
        """
        Multiple transitions are returned oldest-first.

        :return: None
        """
        create_resp = client.post("/bookings", json=VALID_PAYLOAD)
        booking_id = create_resp.json()["id"]
        client.patch(f"/bookings/{booking_id}/status", json={"status": "confirmed"})
        client.patch(f"/bookings/{booking_id}/status", json={"status": "completed"})
        response = client.get(f"/bookings/{booking_id}/timeline")
        assert response.status_code == 200
        entries = response.json()
        assert len(entries) == 2
        assert entries[0]["new_status"] == "confirmed"
        assert entries[1]["new_status"] == "completed"

    def test_missing_booking_returns_404(self, client):
        """
        Timeline request for a non-existent booking id returns HTTP 404.

        :return: None
        """
        response = client.get("/bookings/999999/timeline")
        assert response.status_code == 404
