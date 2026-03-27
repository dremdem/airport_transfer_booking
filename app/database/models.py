"""SQLAlchemy ORM model definitions for the airport transfer booking service.

These are database-layer representations only — domain models live in app/domain/
and contain no SQLAlchemy imports.
"""

import datetime

import sqlalchemy
import sqlalchemy.orm


Base = sqlalchemy.orm.declarative_base()


def utcnow_naive() -> datetime.datetime:
    """
    Return the current UTC time as a naive datetime (no tzinfo).

    MySQL's DATETIME type has no timezone support, so all timestamps are stored
    as naive values.  Using UTC as the source keeps them consistent across
    environments regardless of the server's local timezone.

    :return: current UTC time without tzinfo
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class BookingORM(Base):
    """
    ORM model for the ``booking`` table.

    Stores the core booking data with a composite index on (pickup_time, status)
    to support efficient date-range + status queries.
    """

    __tablename__ = "booking"
    __table_args__ = (
        sqlalchemy.Index("ix_booking_pickup_time_status", "pickup_time", "status"),
    )

    id = sqlalchemy.Column(sqlalchemy.BigInteger, primary_key=True, autoincrement=True)
    passenger_name = sqlalchemy.Column(sqlalchemy.String(255), nullable=False)
    flight_number = sqlalchemy.Column(sqlalchemy.String(50), nullable=False)
    pickup_time = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    pickup_location = sqlalchemy.Column(sqlalchemy.String(255), nullable=False)
    dropoff_location = sqlalchemy.Column(sqlalchemy.String(255), nullable=False)
    status = sqlalchemy.Column(sqlalchemy.String(20), nullable=False)
    created_at = sqlalchemy.Column(
        sqlalchemy.DateTime,
        nullable=False,
        default=utcnow_naive,
    )
    updated_at = sqlalchemy.Column(
        sqlalchemy.DateTime,
        nullable=False,
        default=utcnow_naive,
        onupdate=utcnow_naive,
    )

    status_history = sqlalchemy.orm.relationship(
        "BookingStatusHistoryORM",
        back_populates="booking",
    )
    notification_logs = sqlalchemy.orm.relationship(
        "NotificationLogORM",
        back_populates="booking",
    )


class BookingStatusHistoryORM(Base):
    """
    ORM model for the ``booking_status_history`` table.

    Records every status transition for a booking, enabling full audit trails.
    Indexed on booking_id for efficient per-booking history lookups.
    """

    __tablename__ = "booking_status_history"
    __table_args__ = (
        sqlalchemy.Index("ix_booking_status_history_booking_id", "booking_id"),
    )

    id = sqlalchemy.Column(sqlalchemy.BigInteger, primary_key=True, autoincrement=True)
    booking_id = sqlalchemy.Column(
        sqlalchemy.BigInteger,
        sqlalchemy.ForeignKey("booking.id"),
        nullable=False,
    )
    old_status = sqlalchemy.Column(sqlalchemy.String(20), nullable=True)
    new_status = sqlalchemy.Column(sqlalchemy.String(20), nullable=False)
    created_at = sqlalchemy.Column(
        sqlalchemy.DateTime,
        nullable=False,
        default=utcnow_naive,
    )

    booking = sqlalchemy.orm.relationship("BookingORM", back_populates="status_history")


class NotificationLogORM(Base):
    """
    ORM model for the ``notification_log`` table.

    Tracks outbound notification events triggered by booking lifecycle changes.
    Indexed on booking_id for efficient per-booking notification lookups.
    """

    __tablename__ = "notification_log"
    __table_args__ = (
        sqlalchemy.Index("ix_notification_log_booking_id", "booking_id"),
    )

    id = sqlalchemy.Column(sqlalchemy.BigInteger, primary_key=True, autoincrement=True)
    booking_id = sqlalchemy.Column(
        sqlalchemy.BigInteger,
        sqlalchemy.ForeignKey("booking.id"),
        nullable=False,
    )
    event_type = sqlalchemy.Column(sqlalchemy.String(100), nullable=False)
    message = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    created_at = sqlalchemy.Column(
        sqlalchemy.DateTime,
        nullable=False,
        default=utcnow_naive,
    )

    booking = sqlalchemy.orm.relationship("BookingORM", back_populates="notification_logs")
