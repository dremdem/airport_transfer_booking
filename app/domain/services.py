"""Booking domain service — orchestrates business rules and repository calls."""

import datetime
import typing

import app.domain.enums as enums
import app.domain.exceptions as exceptions
import app.domain.models as models

# TYPE_CHECKING is False at runtime, so this import never executes in production.
# It exists only for static type checkers (mypy/pyright) to resolve the type hint
# on BookingService.__init__. Importing repository unconditionally would create a
# circular dependency once database.repository imports from domain in later phases.
if typing.TYPE_CHECKING:
    import app.database.repository as repository


class BookingService:
    """
    Orchestrates all booking-related business logic.

    Receives a repository via constructor injection so it can be tested
    with a mock repository without touching the database.
    """
    def __init__(self, repo: "repository.BookingRepository") -> None:
        """
        Initialise the service with its repository dependency.

        :param repo: booking repository instance
        """
        self._repo = repo

    def create(self, booking_input: models.BookingInput) -> models.Booking:
        """
        Create a new booking, actively setting PENDING as the initial status.

        The service constructs a ``BookingCreate`` command with ``status=PENDING``
        before calling the repository.  This keeps the invariant in the domain
        layer where it belongs; the repository is a passive persister.

        :param booking_input: validated input data from the application layer
        :return: persisted Booking domain entity
        """
        booking_create = models.BookingCreate(
            passenger_name=booking_input.passenger_name,
            flight_number=booking_input.flight_number,
            pickup_time=booking_input.pickup_time,
            pickup_location=booking_input.pickup_location,
            dropoff_location=booking_input.dropoff_location,
            status=enums.BookingStatus.PENDING,
        )
        return self._repo.create(booking_create)

    def get_by_id(self, booking_id: int) -> models.Booking:
        """
        Retrieve a booking by its primary key.

        :param booking_id: numeric booking identifier
        :return: Booking domain entity
        :raises BookingNotFoundError: if no booking with that ID exists
        """
        booking = self._repo.get_by_id(booking_id)
        if booking is None:
            raise exceptions.BookingNotFoundError(booking_id)
        return booking

    def update_status(self, booking_id: int, new_status: enums.BookingStatus) -> models.Booking:
        """
        Transition a booking to a new status if the transition is permitted.

        :param booking_id: numeric booking identifier
        :param new_status: the desired target status
        :return: updated Booking domain entity
        :raises BookingNotFoundError: if no booking with that ID exists
        :raises InvalidStatusTransitionError: if the transition is not allowed
        """
        booking = self.get_by_id(booking_id)
        if new_status not in enums.VALID_TRANSITIONS[booking.status]:
            raise exceptions.InvalidStatusTransitionError(booking.status, new_status)
        return self._repo.update_status(booking_id, new_status, booking.status)

    def get_timeline(self, booking_id: int) -> list[models.BookingTimelineEntry]:
        """
        Return the full status-transition history for a booking, ordered chronologically.

        Existence is verified first so that an unknown ``booking_id`` raises
        ``BookingNotFoundError`` (→ 404) rather than silently returning an
        empty list.

        When no transitions have been recorded yet, a single synthetic entry is
        returned representing the booking's initial creation state.  Its
        ``old_status`` is ``None`` (no prior state exists) and ``transitioned_at``
        is the booking's ``created_at`` timestamp.

        :param booking_id: numeric booking identifier
        :return: list of BookingTimelineEntry from earliest to latest transition;
                 always contains at least one entry for existing bookings
        :raises BookingNotFoundError: if no booking with that ID exists
        """
        booking = self.get_by_id(booking_id)
        entries = self._repo.get_timeline(booking_id)
        if not entries:
            return [models.BookingTimelineEntry(
                booking_id=booking.id,
                passenger_name=booking.passenger_name,
                flight_number=booking.flight_number,
                pickup_time=booking.pickup_time,
                pickup_location=booking.pickup_location,
                dropoff_location=booking.dropoff_location,
                current_status=booking.status,
                old_status=None,
                new_status=booking.status,
                transitioned_at=booking.created_at,
            )]
        return entries

    def list_by_date(self, date: datetime.date) -> list[models.Booking]:
        """
        Return all bookings whose pickup time falls on the given date.

        :param date: the calendar date to filter by
        :return: list of matching Booking domain entities
        """
        return self._repo.list_by_date(date)
