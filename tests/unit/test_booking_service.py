"""Unit tests for BookingService domain logic.

Tests cover status transition rules, default status on creation, and
invalid transition rejection. No database or HTTP involved.
"""

import datetime
import unittest.mock

import pytest

import app.domain.enums as enums
import app.domain.exceptions as exceptions
import app.domain.models as models
import app.domain.services as services


def make_booking(**kwargs) -> models.Booking:
    """
    Build a Booking domain object with sensible defaults for testing.

    :param kwargs: field overrides
    :return: Booking instance
    """
    defaults = dict(
        id=1,
        passenger_name="Alice Smith",
        flight_number="BA123",
        pickup_time=datetime.datetime(2025, 6, 1, 10, 0),
        pickup_location="Heathrow T2",
        dropoff_location="City Hotel",
        status=enums.BookingStatus.PENDING,
        created_at=datetime.datetime(2025, 6, 1, 8, 0),
        updated_at=datetime.datetime(2025, 6, 1, 8, 0),
    )
    defaults.update(kwargs)
    return models.Booking(**defaults)


def make_service(booking: models.Booking | None = None) -> services.BookingService:
    """
    Build a BookingService backed by a mock repository.

    :param booking: the Booking the mock repository returns for get/create calls
    :return: BookingService with injected mock repository
    """
    repo = unittest.mock.MagicMock()
    repo.create.return_value = booking or make_booking()
    repo.get_by_id.return_value = booking or make_booking()
    return services.BookingService(repo)


BOOKING_INPUT = models.BookingInput(
    passenger_name="Alice Smith",
    flight_number="BA123",
    pickup_time=datetime.datetime(2025, 6, 1, 10, 0),
    pickup_location="Heathrow T2",
    dropoff_location="City Hotel",
)


class TestCreateBooking:
    """Tests for BookingService.create."""

    def test_create_returns_pending_booking(self):
        """
        Service returns the booking produced by the repository.

        :return: None
        """
        service = make_service(make_booking(status=enums.BookingStatus.PENDING))
        result = service.create(BOOKING_INPUT)
        assert result.status == enums.BookingStatus.PENDING

    def test_create_passes_pending_status_to_repo(self):
        """
        Service actively sets PENDING when constructing the BookingCreate command,
        proving the invariant lives in the domain layer rather than in the repository.

        :return: None
        """
        repo = unittest.mock.MagicMock()
        repo.create.return_value = make_booking(status=enums.BookingStatus.PENDING)
        service = services.BookingService(repo)
        service.create(BOOKING_INPUT)
        call_arg = repo.create.call_args[0][0]
        assert isinstance(call_arg, models.BookingCreate)
        assert call_arg.status == enums.BookingStatus.PENDING


class TestStatusTransitions:
    """Tests for BookingService.update_status transition rules."""

    @pytest.mark.parametrize("from_status,to_status", [
        (enums.BookingStatus.PENDING, enums.BookingStatus.CONFIRMED),
        (enums.BookingStatus.PENDING, enums.BookingStatus.CANCELLED),
        (enums.BookingStatus.CONFIRMED, enums.BookingStatus.COMPLETED),
        (enums.BookingStatus.CONFIRMED, enums.BookingStatus.CANCELLED),
    ])
    def test_valid_status_transitions(self, from_status, to_status):
        """
        All valid transitions in the state machine succeed without raising.

        :param from_status: current booking status
        :param to_status: requested target status
        :return: None
        """
        booking = make_booking(status=from_status)
        repo = unittest.mock.MagicMock()
        repo.get_by_id.return_value = booking
        repo.update_status.return_value = make_booking(status=to_status)
        service = services.BookingService(repo)
        result = service.update_status(booking_id=1, new_status=to_status)
        assert result.status == to_status

    @pytest.mark.parametrize("from_status,to_status", [
        (enums.BookingStatus.COMPLETED, enums.BookingStatus.PENDING),
        (enums.BookingStatus.COMPLETED, enums.BookingStatus.CONFIRMED),
        (enums.BookingStatus.COMPLETED, enums.BookingStatus.CANCELLED),
        (enums.BookingStatus.CANCELLED, enums.BookingStatus.PENDING),
        (enums.BookingStatus.CANCELLED, enums.BookingStatus.CONFIRMED),
        (enums.BookingStatus.PENDING, enums.BookingStatus.COMPLETED),
    ])
    def test_invalid_status_transitions(self, from_status, to_status):
        """
        Disallowed transitions raise InvalidStatusTransitionError.

        :param from_status: current booking status
        :param to_status: requested target status
        :return: None
        """
        booking = make_booking(status=from_status)
        service = make_service(booking)
        with pytest.raises(exceptions.InvalidStatusTransitionError):
            service.update_status(booking_id=1, new_status=to_status)
