"""Domain entities for the booking service.

These are plain Python dataclasses — no ORM, no HTTP framework.
They represent business concepts, not database rows.
"""

import dataclasses
import datetime

import app.domain.enums as enums


@dataclasses.dataclass
class BookingInput:
    """
    Input data required to create a new booking.

    Passed from the application layer to the domain service after mapping
    from the API request schema.
    """
    passenger_name: str
    flight_number: str
    pickup_time: datetime.datetime
    pickup_location: str
    dropoff_location: str


@dataclasses.dataclass
class BookingCreate:
    """
    Internal command object constructed by the service layer before persisting.

    Carries all ``BookingInput`` fields plus the ``status`` decided by the
    service. The repository accepts this type and persists exactly what it
    receives — no business rules hidden in the data layer.
    """

    passenger_name: str
    flight_number: str
    pickup_time: datetime.datetime
    pickup_location: str
    dropoff_location: str
    status: enums.BookingStatus


@dataclasses.dataclass
class Booking:
    """Full booking domain entity including identity and current state."""
    id: int
    passenger_name: str
    flight_number: str
    pickup_time: datetime.datetime
    pickup_location: str
    dropoff_location: str
    status: enums.BookingStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
