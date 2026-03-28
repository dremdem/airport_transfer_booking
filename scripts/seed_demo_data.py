"""Seed the database with a demo dataset for manual exploration and UI demonstration.

Each run appends a fresh set of bookings — it does not check for existing data and
does not wipe the database first. Run it once before a demo session; run it again
if you want more rows.

Usage (inside Docker):
    docker compose run --rm app python -m scripts.seed_demo_data

Usage via Makefile:
    make seed-demo
"""

import datetime
import sys

import app.database.repository as repository
import app.database.session as db_session
import app.domain.enums as enums
import app.domain.models as domain_models


_BOOKINGS = [
    # ── Pending ────────────────────────────────────────────────────────────
    dict(
        passenger_name="Ellie Arroway",
        flight_number="VG001",
        pickup_time=datetime.datetime(2025, 9, 15, 6, 30),
        pickup_location="Heathrow T5",
        dropoff_location="Royal Observatory, Greenwich",
        final_status=enums.BookingStatus.PENDING,
    ),
    dict(
        passenger_name="Duncan Idaho",
        flight_number="AT214",
        pickup_time=datetime.datetime(2025, 9, 15, 14, 0),
        pickup_location="Gatwick South Terminal",
        dropoff_location="Imperial War Museum",
        final_status=enums.BookingStatus.PENDING,
    ),
    # ── Confirmed ──────────────────────────────────────────────────────────
    dict(
        passenger_name="Naomi Nagata",
        flight_number="MC042",
        pickup_time=datetime.datetime(2025, 9, 16, 9, 15),
        pickup_location="London City Airport",
        dropoff_location="Canary Wharf, One Canada Square",
        final_status=enums.BookingStatus.CONFIRMED,
    ),
    dict(
        passenger_name="Roy Batty",
        flight_number="TY888",
        pickup_time=datetime.datetime(2025, 9, 16, 21, 0),
        pickup_location="Stansted Airport",
        dropoff_location="Tannhäuser Gate Hotel, Southwark",
        final_status=enums.BookingStatus.CONFIRMED,
    ),
    # ── Completed ──────────────────────────────────────────────────────────
    dict(
        passenger_name="Amos Burton",
        flight_number="RB307",
        pickup_time=datetime.datetime(2025, 9, 14, 7, 45),
        pickup_location="Luton Airport",
        dropoff_location="East India Club, St James's Square",
        final_status=enums.BookingStatus.COMPLETED,
    ),
    dict(
        passenger_name="Chrisjen Avasarala",
        flight_number="UN001",
        pickup_time=datetime.datetime(2025, 9, 13, 11, 0),
        pickup_location="Heathrow T3",
        dropoff_location="Foreign, Commonwealth & Development Office",
        final_status=enums.BookingStatus.COMPLETED,
    ),
    # ── Cancelled ──────────────────────────────────────────────────────────
    dict(
        passenger_name="Alex Kamal",
        flight_number="MC777",
        pickup_time=datetime.datetime(2025, 9, 17, 16, 30),
        pickup_location="Gatwick North Terminal",
        dropoff_location="Wembley Stadium",
        final_status=enums.BookingStatus.CANCELLED,
    ),
]

_TRANSITION_PATH: dict[enums.BookingStatus, list[enums.BookingStatus]] = {
    enums.BookingStatus.PENDING:   [],
    enums.BookingStatus.CONFIRMED: [enums.BookingStatus.CONFIRMED],
    enums.BookingStatus.COMPLETED: [enums.BookingStatus.CONFIRMED, enums.BookingStatus.COMPLETED],
    enums.BookingStatus.CANCELLED: [enums.BookingStatus.CANCELLED],
}


def seed() -> None:
    """
    Insert demo bookings and drive each one to its target status.

    Opens a single session for all writes so the whole seed is one unit
    of work. Prints a summary line for each booking created.

    :return: None
    """
    SessionFactory = db_session.SessionLocal
    with SessionFactory() as session:
        repo = repository.BookingRepository(session)
        for spec in _BOOKINGS:
            final_status: enums.BookingStatus = spec["final_status"]
            booking_create = domain_models.BookingCreate(
                **{k: v for k, v in spec.items() if k != "final_status"},
                status=enums.BookingStatus.PENDING,
            )
            booking = repo.create(booking_create)
            current_status = enums.BookingStatus.PENDING
            for step in _TRANSITION_PATH[final_status]:
                booking = repo.update_status(booking.id, step, current_status)
                current_status = step
            print(
                f"  [{booking.status.value:>9}]  #{booking.id:<5} "
                f"{booking.pickup_time.strftime('%Y-%m-%d %H:%M')}  "
                f"{booking.passenger_name} — {booking.pickup_location} → {booking.dropoff_location}"
            )
    print(f"\n✓ Seeded {len(_BOOKINGS)} demo bookings.")


if __name__ == "__main__":
    print("Seeding demo data…\n")
    try:
        seed()
    except Exception as exc:
        print(f"\n✗ Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
