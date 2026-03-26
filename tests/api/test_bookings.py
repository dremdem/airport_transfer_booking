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
