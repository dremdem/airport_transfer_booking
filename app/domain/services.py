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
        Create a new booking and enforce that it starts with PENDING status.

        The PENDING-on-creation rule is a domain invariant. The service verifies
        it after the repository call so the rule is owned by the domain layer,
        not delegated silently to persistence.

        :param booking_input: validated input data from the application layer
        :return: persisted Booking domain entity
        :raises InvalidStatusTransitionError: if the repository violates the PENDING invariant
        """
        booking = self._repo.create(booking_input)
        if booking.status != enums.BookingStatus.PENDING:
            raise exceptions.InvalidStatusTransitionError(
                from_status="(none)",
                to_status=booking.status.value,
            )
        return booking

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

    def list_by_date(self, date: datetime.date) -> list[models.Booking]:
        """
        Return all bookings whose pickup time falls on the given date.

        :param date: the calendar date to filter by
        :return: list of matching Booking domain entities
        """
        return self._repo.list_by_date(date)
