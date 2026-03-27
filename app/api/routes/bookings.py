"""Route handlers for the /bookings endpoints."""

import datetime

import fastapi
import sqlalchemy.orm

import app.api.dependencies as dependencies
import app.api.schemas.bookings as schemas
import app.database.repository as repository
import app.domain.models as domain_models
import app.domain.services as services
import app.integration.notifications as notifications


router = fastapi.APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", status_code=201, response_model=schemas.BookingResponse)
def create_booking(
    body: schemas.BookingCreate,
    background_tasks: fastapi.BackgroundTasks,
    db: sqlalchemy.orm.Session = fastapi.Depends(dependencies.get_db),
) -> schemas.BookingResponse:
    """
    Create a new booking and enqueue a notification background task.

    :param body: validated create request body
    :param background_tasks: FastAPI background task queue
    :param db: database session provided by dependency injection
    :return: the newly created booking
    """
    svc = services.BookingService(repository.BookingRepository(db))
    booking = svc.create(domain_models.BookingInput(
        passenger_name=body.passenger_name,
        flight_number=body.flight_number,
        pickup_time=body.pickup_time,
        pickup_location=body.pickup_location,
        dropoff_location=body.dropoff_location,
    ))
    # Enqueue notification after the booking is committed so the HTTP response
    # is returned immediately. The task must open its own DB session — reusing
    # the request-scoped `db` session causes transaction-boundary problems
    # because that session is closed once this handler returns.
    # See docs/architecture.md — §7 Background Notification Flow.
    background_tasks.add_task(notifications.send_notification, booking.id)
    return schemas.BookingResponse.model_validate(booking)


@router.get("/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(
    booking_id: int,
    db: sqlalchemy.orm.Session = fastapi.Depends(dependencies.get_db),
) -> schemas.BookingResponse:
    """
    Retrieve a booking by its numeric id.

    :param booking_id: numeric booking identifier from the URL path
    :param db: database session provided by dependency injection
    :return: the matching booking
    :raises BookingNotFoundError: translated to 404 by the app exception handler
    """
    svc = services.BookingService(repository.BookingRepository(db))
    return schemas.BookingResponse.model_validate(svc.get_by_id(booking_id))


@router.patch("/{booking_id}/status", response_model=schemas.BookingResponse)
def update_booking_status(
    booking_id: int,
    body: schemas.BookingStatusUpdate,
    db: sqlalchemy.orm.Session = fastapi.Depends(dependencies.get_db),
) -> schemas.BookingResponse:
    """
    Transition a booking to a new status.

    :param booking_id: numeric booking identifier from the URL path
    :param body: validated status update body
    :param db: database session provided by dependency injection
    :return: the booking with the updated status
    :raises BookingNotFoundError: translated to 404 by the app exception handler
    :raises InvalidStatusTransitionError: translated to 422 by the app exception handler
    """
    svc = services.BookingService(repository.BookingRepository(db))
    return schemas.BookingResponse.model_validate(
        svc.update_status(booking_id, body.status)
    )


@router.get("", response_model=list[schemas.BookingResponse])
def list_bookings_by_date(
    date: datetime.date,
    db: sqlalchemy.orm.Session = fastapi.Depends(dependencies.get_db),
) -> list[schemas.BookingResponse]:
    """
    Return all bookings whose pickup time falls on the given date.

    :param date: calendar date query parameter (``?date=YYYY-MM-DD``)
    :param db: database session provided by dependency injection
    :return: list of matching bookings, empty if none found
    """
    svc = services.BookingService(repository.BookingRepository(db))
    return [
        schemas.BookingResponse.model_validate(b)
        for b in svc.list_by_date(date)
    ]
