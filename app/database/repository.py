"""BookingRepository — data access layer for booking persistence operations."""

import datetime

import sqlalchemy
import sqlalchemy.orm

import app.database.models as db_models
import app.domain.enums as enums
import app.domain.models as domain_models


class BookingRepository:
    """
    Provides CRUD and query operations for bookings backed by SQLAlchemy.

    All methods return domain model objects; ORM rows are never exposed outside
    this class, keeping the domain layer free of SQLAlchemy dependencies.
    """

    def __init__(self, db: sqlalchemy.orm.Session) -> None:
        """
        Initialise the repository with an injected SQLAlchemy session.

        :param db: active SQLAlchemy session (typically provided by get_db())
        """
        self._db = db

    def _to_domain(self, orm_booking: db_models.BookingORM) -> domain_models.Booking:
        """
        Map a BookingORM row to a domain Booking dataclass.

        :param orm_booking: ORM row fetched from the database
        :return: domain Booking with the same field values
        """
        return domain_models.Booking(
            id=orm_booking.id,
            passenger_name=orm_booking.passenger_name,
            flight_number=orm_booking.flight_number,
            pickup_time=orm_booking.pickup_time,
            pickup_location=orm_booking.pickup_location,
            dropoff_location=orm_booking.dropoff_location,
            status=enums.BookingStatus(orm_booking.status),
            created_at=orm_booking.created_at,
            updated_at=orm_booking.updated_at,
        )

    def create(self, booking_create: domain_models.BookingCreate) -> domain_models.Booking:
        """
        Persist a new booking from a service-layer command and return the domain entity.

        The repository does not enforce any status rules — it persists exactly
        the state provided in ``booking_create``.

        :param booking_create: internal command object constructed by the service layer
        :return: persisted Booking domain entity with assigned id and timestamps
        """
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        orm_booking = db_models.BookingORM(
            passenger_name=booking_create.passenger_name,
            flight_number=booking_create.flight_number,
            pickup_time=booking_create.pickup_time,
            pickup_location=booking_create.pickup_location,
            dropoff_location=booking_create.dropoff_location,
            status=booking_create.status.value,
            created_at=now,
            updated_at=now,
        )
        self._db.add(orm_booking)
        self._db.commit()
        self._db.refresh(orm_booking)
        return self._to_domain(orm_booking)

    def get_by_id(self, booking_id: int) -> domain_models.Booking | None:
        """
        Retrieve a booking by its primary key.

        :param booking_id: numeric booking identifier
        :return: Booking domain entity, or None if not found
        """
        orm_booking = self._db.get(db_models.BookingORM, booking_id)
        if orm_booking is None:
            return None
        return self._to_domain(orm_booking)

    def list_by_date(self, date: datetime.date) -> list[domain_models.Booking]:
        """
        Return all bookings whose pickup_time falls on the given calendar date.

        Uses a half-open interval [start_of_day, start_of_next_day) to avoid
        microsecond edge cases with datetime.time.max.

        :param date: the calendar date to filter by
        :return: list of matching Booking domain entities
        """
        start = datetime.datetime.combine(date, datetime.time.min)
        end = datetime.datetime.combine(
            date + datetime.timedelta(days=1), datetime.time.min
        )
        orm_bookings = (
            self._db.query(db_models.BookingORM)
            .filter(
                db_models.BookingORM.pickup_time >= start,
                db_models.BookingORM.pickup_time < end,
            )
            .all()
        )
        return [self._to_domain(b) for b in orm_bookings]

    def get_timeline(self, booking_id: int) -> list[domain_models.BookingTimelineEntry]:
        """
        Fetch all status-transition rows for a booking from the timeline view.

        Rows are ordered chronologically by history_id (insertion order).
        Returns an empty list when the booking has no recorded transitions yet.
        Existence checking is the caller's responsibility (BookingService does it).

        :param booking_id: numeric booking identifier
        :return: list of BookingTimelineEntry ordered from earliest to latest
        """
        result = self._db.execute(
            sqlalchemy.text(
                "SELECT booking_id, passenger_name, flight_number, pickup_time,"
                " pickup_location, dropoff_location, current_status,"
                " old_status, new_status, transitioned_at"
                " FROM booking_timeline_view"
                " WHERE booking_id = :booking_id"
                " ORDER BY history_id ASC"
            ),
            {"booking_id": booking_id},
        )
        return [
            domain_models.BookingTimelineEntry(
                booking_id=row.booking_id,
                passenger_name=row.passenger_name,
                flight_number=row.flight_number,
                pickup_time=row.pickup_time,
                pickup_location=row.pickup_location,
                dropoff_location=row.dropoff_location,
                current_status=enums.BookingStatus(row.current_status),
                old_status=enums.BookingStatus(row.old_status),
                new_status=enums.BookingStatus(row.new_status),
                transitioned_at=row.transitioned_at,
            )
            for row in result.mappings()
        ]

    def update_status(
        self,
        booking_id: int,
        new_status: enums.BookingStatus,
        old_status: enums.BookingStatus,
    ) -> domain_models.Booking:
        """
        Update a booking's status and atomically append a status history row.

        Both the booking update and the history insert are committed in a single
        transaction, ensuring the audit trail is always consistent.

        :param booking_id: numeric booking identifier
        :param new_status: the target status to transition to
        :param old_status: the current status before transition (written to history)
        :return: updated Booking domain entity
        """
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        orm_booking = self._db.get(db_models.BookingORM, booking_id)
        orm_booking.status = new_status.value
        orm_booking.updated_at = now
        history = db_models.BookingStatusHistoryORM(
            booking_id=booking_id,
            old_status=old_status.value,
            new_status=new_status.value,
            created_at=now,
        )
        self._db.add(history)
        self._db.commit()
        self._db.refresh(orm_booking)
        return self._to_domain(orm_booking)
