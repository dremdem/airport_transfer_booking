"""Notification side-effects triggered by booking lifecycle events."""

import app.database.models as db_models
import app.database.session as session


def send_notification(booking_id: int) -> None:
    """
    Write a notification log entry for a booking creation event.

    Opens its own ``SessionLocal`` session — independent of the request-scoped
    session that is already closed by the time this background task runs.
    Both writes are separate units of work: the booking is committed on the
    main request path; this notification write is committed here.

    :param booking_id: numeric identifier of the booking that triggered the event
    :return: None
    """
    with session.SessionLocal() as db:
        entry = db_models.NotificationLogORM(
            booking_id=booking_id,
            event_type="booking_created",
            message=f"Booking {booking_id} created successfully.",
        )
        db.add(entry)
        db.commit()
