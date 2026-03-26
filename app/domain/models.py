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

    :param passenger_name: full name of the passenger
    :param flight_number: flight identifier string
    :param pickup_time: scheduled pickup datetime
    :param pickup_location: pickup address or terminal description
    :param dropoff_location: dropoff address or terminal description
    """
    passenger_name: str
    flight_number: str
    pickup_time: datetime.datetime
    pickup_location: str
    dropoff_location: str


@dataclasses.dataclass
class Booking:
    """
    Full booking domain entity including identity and current state.

    :param id: numeric primary key
    :param passenger_name: full name of the passenger
    :param flight_number: flight identifier string
    :param pickup_time: scheduled pickup datetime
    :param pickup_location: pickup address or terminal description
    :param dropoff_location: dropoff address or terminal description
    :param status: current lifecycle status
    :param created_at: timestamp when the booking was created
    :param updated_at: timestamp of the last update
    """
    id: int
    passenger_name: str
    flight_number: str
    pickup_time: datetime.datetime
    pickup_location: str
    dropoff_location: str
    status: enums.BookingStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
