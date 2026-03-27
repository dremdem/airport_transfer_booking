"""Pydantic request and response schemas for the bookings API."""

import datetime

import pydantic

import app.domain.enums as enums


class BookingCreate(pydantic.BaseModel):
    """
    Request body for POST /bookings.

    Carries only the fields provided by the caller; status is assigned by
    the domain service and must not appear in the create request.

    ``extra="forbid"`` ensures unknown fields (e.g. a caller attempting to
    set ``status``) are rejected with 422 rather than silently ignored.
    Field lengths match the DB column sizes defined in architecture.md.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    passenger_name: str = pydantic.Field(min_length=1, max_length=255)
    flight_number: str = pydantic.Field(min_length=1, max_length=20)
    pickup_time: datetime.datetime
    pickup_location: str = pydantic.Field(min_length=1, max_length=500)
    dropoff_location: str = pydantic.Field(min_length=1, max_length=500)


class BookingStatusUpdate(pydantic.BaseModel):
    """Request body for PATCH /bookings/{id}/status."""

    status: enums.BookingStatus


class BookingResponse(pydantic.BaseModel):
    """
    Response schema returned for all booking read and write endpoints.

    ``from_attributes=True`` allows instantiation directly from the domain
    ``Booking`` dataclass without a manual field-by-field mapping in the handler.
    """

    model_config = pydantic.ConfigDict(from_attributes=True)

    id: int
    passenger_name: str
    flight_number: str
    pickup_time: datetime.datetime
    pickup_location: str
    dropoff_location: str
    status: enums.BookingStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
