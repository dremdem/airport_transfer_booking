"""Integration tests for BookingRepository — exercises real MySQL via docker-compose db service."""

import datetime

import app.database.models as db_models
import app.domain.enums as enums
import app.domain.models as domain_models


BOOKING_CREATE = domain_models.BookingCreate(
    passenger_name="Alice Smith",
    flight_number="BA123",
    pickup_time=datetime.datetime(2025, 6, 1, 10, 0),
    pickup_location="Heathrow T2",
    dropoff_location="City Hotel",
    status=enums.BookingStatus.PENDING,
)


class TestCreate:
    """Tests for BookingRepository.create."""

    def test_create_returns_domain_booking(self, repo):
        """
        create() returns a fully-populated domain Booking with an assigned id.

        :return: None
        """
        result = repo.create(BOOKING_CREATE)
        assert result.id is not None
        assert result.passenger_name == "Alice Smith"
        assert result.flight_number == "BA123"
        assert result.pickup_location == "Heathrow T2"
        assert result.dropoff_location == "City Hotel"

    def test_create_sets_pending_status(self, repo):
        """
        New bookings are always persisted with PENDING status.

        :return: None
        """
        result = repo.create(BOOKING_CREATE)
        assert result.status == enums.BookingStatus.PENDING

    def test_create_sets_timestamps(self, repo):
        """
        created_at and updated_at are populated on creation.

        :return: None
        """
        result = repo.create(BOOKING_CREATE)
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_create_persists_to_db(self, repo, db_session):
        """
        The created row is readable from the same session after commit.

        :return: None
        """
        result = repo.create(BOOKING_CREATE)
        db_session.expire_all()
        orm_row = db_session.get(db_models.BookingORM, result.id)
        assert orm_row is not None
        assert orm_row.passenger_name == "Alice Smith"


class TestGetById:
    """Tests for BookingRepository.get_by_id."""

    def test_get_by_id_returns_booking(self, repo):
        """
        get_by_id returns the booking matching the given id.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        result = repo.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id
        assert result.passenger_name == "Alice Smith"

    def test_get_by_id_returns_none_for_missing(self, repo):
        """
        get_by_id returns None when no booking with that id exists.

        :return: None
        """
        result = repo.get_by_id(999999)
        assert result is None


class TestListByDate:
    """Tests for BookingRepository.list_by_date."""

    def test_list_by_date_returns_bookings_on_that_date(self, repo):
        """
        list_by_date returns bookings whose pickup_time falls on the given date.

        :return: None
        """
        repo.create(BOOKING_CREATE)
        result = repo.list_by_date(datetime.date(2025, 6, 1))
        assert len(result) == 1
        assert result[0].passenger_name == "Alice Smith"

    def test_list_by_date_excludes_other_dates(self, repo):
        """
        list_by_date does not return bookings from other dates.

        :return: None
        """
        repo.create(BOOKING_CREATE)
        result = repo.list_by_date(datetime.date(2025, 6, 2))
        assert len(result) == 0

    def test_list_by_date_returns_multiple_bookings(self, repo):
        """
        list_by_date returns all bookings on the given date.

        :return: None
        """
        second = domain_models.BookingCreate(
            passenger_name="Bob Jones",
            flight_number="LH456",
            pickup_time=datetime.datetime(2025, 6, 1, 14, 30),
            pickup_location="Gatwick N",
            dropoff_location="Another Hotel",
            status=enums.BookingStatus.PENDING,
        )
        repo.create(BOOKING_CREATE)
        repo.create(second)
        result = repo.list_by_date(datetime.date(2025, 6, 1))
        assert len(result) == 2


class TestUpdateStatus:
    """Tests for BookingRepository.update_status."""

    def test_update_status_changes_booking_status(self, repo):
        """
        update_status returns the booking with the new status applied.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        result = repo.update_status(
            created.id,
            enums.BookingStatus.CONFIRMED,
            enums.BookingStatus.PENDING,
        )
        assert result.status == enums.BookingStatus.CONFIRMED

    def test_update_status_creates_history_entry(self, repo, db_session):
        """
        update_status inserts a booking_status_history row in the same transaction.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        repo.update_status(
            created.id,
            enums.BookingStatus.CONFIRMED,
            enums.BookingStatus.PENDING,
        )
        db_session.expire_all()
        history = (
            db_session.query(db_models.BookingStatusHistoryORM)
            .filter_by(booking_id=created.id)
            .all()
        )
        assert len(history) == 1
        assert history[0].old_status == enums.BookingStatus.PENDING
        assert history[0].new_status == enums.BookingStatus.CONFIRMED

    def test_update_status_updates_updated_at(self, repo):
        """
        update_status refreshes the updated_at timestamp on the booking.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        result = repo.update_status(
            created.id,
            enums.BookingStatus.CONFIRMED,
            enums.BookingStatus.PENDING,
        )
        assert result.updated_at >= created.updated_at

    def test_update_status_multiple_transitions_accumulate_history(self, repo, db_session):
        """
        Each call to update_status appends a new history row.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        repo.update_status(created.id, enums.BookingStatus.CONFIRMED, enums.BookingStatus.PENDING)
        repo.update_status(created.id, enums.BookingStatus.COMPLETED, enums.BookingStatus.CONFIRMED)
        db_session.expire_all()
        history = (
            db_session.query(db_models.BookingStatusHistoryORM)
            .filter_by(booking_id=created.id)
            .order_by(db_models.BookingStatusHistoryORM.id)
            .all()
        )
        assert len(history) == 2
        assert history[0].new_status == enums.BookingStatus.CONFIRMED
        assert history[1].new_status == enums.BookingStatus.COMPLETED


class TestGetTimeline:
    """Tests for BookingRepository.get_timeline."""

    def test_returns_empty_list_for_booking_with_no_transitions(self, repo):
        """
        A booking that has never been transitioned returns an empty timeline.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        result = repo.get_timeline(created.id)
        assert result == []

    def test_returns_one_entry_after_one_transition(self, repo):
        """
        A single status transition produces one timeline entry.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        repo.update_status(created.id, enums.BookingStatus.CONFIRMED, enums.BookingStatus.PENDING)
        result = repo.get_timeline(created.id)
        assert len(result) == 1
        assert result[0].old_status == enums.BookingStatus.PENDING
        assert result[0].new_status == enums.BookingStatus.CONFIRMED
        assert result[0].booking_id == created.id

    def test_entries_ordered_chronologically(self, repo):
        """
        Multiple transitions are returned earliest-first.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        repo.update_status(created.id, enums.BookingStatus.CONFIRMED, enums.BookingStatus.PENDING)
        repo.update_status(created.id, enums.BookingStatus.COMPLETED, enums.BookingStatus.CONFIRMED)
        result = repo.get_timeline(created.id)
        assert len(result) == 2
        assert result[0].new_status == enums.BookingStatus.CONFIRMED
        assert result[1].new_status == enums.BookingStatus.COMPLETED

    def test_entry_contains_booking_fields(self, repo):
        """
        Each timeline entry includes the booking's core fields for context.

        :return: None
        """
        created = repo.create(BOOKING_CREATE)
        repo.update_status(created.id, enums.BookingStatus.CONFIRMED, enums.BookingStatus.PENDING)
        entry = repo.get_timeline(created.id)[0]
        assert entry.passenger_name == "Alice Smith"
        assert entry.flight_number == "BA123"
        assert entry.transitioned_at is not None
