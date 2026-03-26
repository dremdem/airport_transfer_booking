"""Domain-specific exceptions for the booking service.

All exceptions are framework-agnostic — no FastAPI or HTTP concepts here.
The application layer is responsible for translating these into HTTP responses.
"""


class BookingNotFoundError(Exception):
    """Raised when a booking with the requested ID does not exist."""
    def __init__(self, booking_id: int) -> None:
        """
        Initialise with the missing booking ID.

        :param booking_id: the ID that was not found
        """
        super().__init__(f"Booking with id {booking_id} not found")
        self.booking_id = booking_id


class InvalidStatusTransitionError(Exception):
    """Raised when a requested status transition is not permitted."""
    def __init__(self, from_status: str, to_status: str) -> None:
        """
        Initialise with the invalid from/to status pair.

        :param from_status: current booking status
        :param to_status: requested target status
        """
        super().__init__(f"Cannot transition from '{from_status}' to '{to_status}'")
        self.from_status = from_status
        self.to_status = to_status
