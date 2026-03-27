# Transfer Booking Service — Final Architecture

## Table of Contents

- [1. Overview](#1-overview)
- [2. Tech Stack](#2-tech-stack)
- [3. Layered Architecture](#3-layered-architecture)
- [4. Database Schema](#4-database-schema)
- [5. API Design](#5-api-design)
- [6. Status State Machine](#6-status-state-machine)
- [7. Background Notification Flow](#7-background-notification-flow)
- [8. Testing Strategy](#8-testing-strategy)
- [9. Docker Compose Setup](#9-docker-compose-setup)
- [10. Configuration Management](#10-configuration-management)
- [11. Design Decisions Summary](#11-design-decisions-summary)

---

## 1. Overview

The **Transfer Booking Service** is a monolithic FastAPI application that manages airport transfer bookings. It handles the full booking lifecycle — creation, confirmation, completion, and cancellation — with a background notification system and a layered codebase designed for maintainability and testability.

The architecture is intentionally kept simple and delivery-focused: one FastAPI application, one MySQL database, containerised with Docker Compose. No microservices, no external message broker.

```mermaid
graph TD
    Client[Client] --> API[Application Layer<br/>app/api/]
    API --> Domain[Domain Layer<br/>app/domain/]
    Domain --> DB[Database Layer<br/>app/database/]
    DB --> MySQL[(MySQL 8.0)]
    API --> Integration[Integration Layer<br/>app/integration/]
    Integration --> MySQL
```

---

## 2. Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | **FastAPI** | Modern Python web framework with built-in Pydantic validation and OpenAPI docs. |
| ORM | **SQLAlchemy 2.0 (sync)** | Simpler mental model. Mature `PyMySQL` driver. No high-concurrency bottleneck for a booking service. Sync endpoints run in FastAPI's threadpool automatically. |
| Migrations | **Alembic** | Standard migration tool for SQLAlchemy. Versioned, reversible schema changes. |
| Database | **MySQL 8.0** | Required by the assignment. Well-suited for transactional booking data. |
| Background tasks | **FastAPI BackgroundTasks** | No external broker needed for a single notification side-effect. Celery would add Redis/RabbitMQ infrastructure with no proportional benefit at this scale. |
| Testing | **pytest + httpx** | `httpx` with `ASGITransport` tests the full ASGI stack without a running server. Enables clean unit/integration separation. |
| Containerisation | **Docker Compose** | Reproducible local environment with zero manual setup. |
| Package installer | **uv** | Replaces `pip` inside the Docker image. Significantly faster dependency resolution and installation. Installed via the official `ghcr.io/astral-sh/uv` image layer — no manual install step needed. |

---

## 3. Layered Architecture

The project follows a four-layer architecture. Each layer has a single responsibility and communicates only with its immediate neighbours.

```
transfer_booking_service/
├── app/
│   ├── api/                        # APPLICATION LAYER
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── bookings.py         # Route handlers (thin controllers)
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── bookings.py         # Pydantic request/response models
│   │   └── dependencies.py         # FastAPI Depends (DB session, etc.)
│   │
│   ├── domain/                     # DOMAIN LAYER
│   │   ├── __init__.py
│   │   ├── models.py               # Domain entities (plain dataclasses)
│   │   ├── services.py             # Business logic (BookingService)
│   │   ├── exceptions.py           # Domain exceptions
│   │   └── enums.py                # BookingStatus enum + transition map
│   │
│   ├── integration/                # INTEGRATION LAYER
│   │   ├── __init__.py
│   │   └── notifications.py        # Notification side-effect (background task)
│   │
│   ├── database/                   # DATABASE LAYER
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── repository.py           # Data access (BookingRepository)
│   │   └── session.py              # Engine, SessionLocal, get_db
│   │
│   ├── config.py                   # Pydantic Settings (env-driven config)
│   └── main.py                     # FastAPI app factory
│
├── alembic/
│   ├── versions/                   # Migration scripts
│   └── env.py
├── tests/
│   ├── unit/                       # Pure logic tests (no DB, no HTTP)
│   │   ├── __init__.py
│   │   └── test_booking_service.py
│   ├── api/                        # HTTP endpoint tests (TestClient + real DB)
│   │   ├── __init__.py
│   │   ├── conftest.py             # client fixture, autouse notification mock
│   │   └── test_bookings.py        # Input validation, status codes, response shape
│   ├── integration/                # Full-stack and repository-layer tests
│   │   ├── __init__.py
│   │   ├── conftest.py             # repo and client fixtures
│   │   ├── test_bookings_api.py    # HTTP → domain → DB round-trip (8 named tests)
│   │   ├── test_booking_repository.py  # Repository layer against real MySQL
│   │   ├── test_notifications.py   # send_notification unit + DB assertions
│   │   └── test_create_notification_e2e.py  # Full route → background task → DB
│   └── conftest.py                 # Shared fixtures (db_engine, db_session)
│
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
├── .env.example
└── README.md
```

### Layer responsibilities

#### Application Layer (`app/api/`)

Accepts HTTP requests, validates input via Pydantic schemas, maps request data to domain inputs, delegates to domain services, formats and returns HTTP responses.

Contains **zero business logic**. Route handlers are 5–10 lines. No status validation, no booking rules, no direct database calls.

**Critical boundary:** Pydantic request models must never be passed directly into domain services. The application layer maps them to domain-level input objects before calling domain logic. This keeps the domain layer independent of FastAPI/Pydantic transport concerns.

```python
@router.post("/bookings", response_model=schemas.BookingResponse, status_code=201)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks,
):
    """
    Create a new booking and enqueue the notification background task.

    :param payload: validated request body
    :param db: database session (request-scoped)
    :param background_tasks: FastAPI background task registry
    :return: created booking response
    """
    booking_input = domain.models.BookingInput(
        passenger_name=payload.passenger_name,
        flight_number=payload.flight_number,
        pickup_time=payload.pickup_time,
        pickup_location=payload.pickup_location,
        dropoff_location=payload.dropoff_location,
    )
    service = domain.services.BookingService(database.repository.BookingRepository(db))
    booking = service.create(booking_input)
    background_tasks.add_task(integration.notifications.send_notification, booking.id)
    return booking
```

#### Domain Layer (`app/domain/`)

Encodes all business rules. Defines what a booking is, what status transitions are legal, and what invariants must hold.

Status transition rules live here as an explicit Python map — not in the database, not in the API layer. Any illegal transition raises a domain exception (`InvalidStatusTransitionError`). This makes rules unit-testable without any infrastructure.

Domain exceptions are raised here and translated to HTTP status codes in the API layer. The domain layer knows nothing about FastAPI, HTTP, or status codes.

```python
VALID_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING:    {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED:  {BookingStatus.COMPLETED, BookingStatus.CANCELLED},
    BookingStatus.COMPLETED:  set(),
    BookingStatus.CANCELLED:  set(),
}
```

**Domain vs ORM models:** Domain objects represent business concepts; ORM models represent database rows. Keeping them separate prevents SQLAlchemy session state (lazy loading, detached instances, identity map) from leaking into business logic.

#### Integration Layer (`app/integration/`)

Handles side effects that cross system boundaries. In this project it contains the notification background task that writes log entries to `notification_log`.

**Critical boundary:** The background task opens and manages its own database session. It must never reuse the request-scoped session. The booking is committed during the main request transaction; the notification write is a separate unit of work. Reusing the same session creates lifecycle and transaction-boundary problems.

```python
def send_notification(booking_id: int) -> None:
    """
    Write a notification log entry for a booking event.

    Opens its own database session — independent of the request session.

    :param booking_id: ID of the booking that triggered this notification
    """
    with database.session.SessionLocal() as db:
        entry = database.models.NotificationLog(
            booking_id=booking_id,
            event_type="booking_created",
            message=f"Booking {booking_id} created successfully.",
        )
        db.add(entry)
        db.commit()
```

#### Database Layer (`app/database/`)

SQLAlchemy ORM models, the session factory, and the repository pattern.

The `BookingRepository` encapsulates all SQL/ORM queries behind a clean interface (`create`, `get_by_id`, `list_by_date`, `update_status`, `record_status_change`). The domain layer never writes raw queries. This also makes unit testing trivial — inject a mock repository to test business logic without a database.

---

## 4. Database Schema

Three tables store booking state, status audit trail, and notification side effects as separate responsibilities.

All table names are **singular** and all primary keys are **BIGINT auto-increment**.

```sql
CREATE TABLE booking (
    id               BIGINT        AUTO_INCREMENT PRIMARY KEY,
    passenger_name   VARCHAR(255)  NOT NULL,
    flight_number    VARCHAR(20)   NOT NULL,
    pickup_time      DATETIME      NOT NULL,
    pickup_location  VARCHAR(500)  NOT NULL,
    dropoff_location VARCHAR(500)  NOT NULL,
    status           VARCHAR(20)   NOT NULL DEFAULT 'pending',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,

    -- Composite index serves both date-only and date+status query patterns.
    -- The leftmost prefix (pickup_time) covers GET /bookings?date=YYYY-MM-DD.
    -- The full index covers operational queries like "today's confirmed bookings".
    INDEX ix_booking_pickup_time_status (pickup_time, status)
);

CREATE TABLE booking_status_history (
    id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
    booking_id  BIGINT       NOT NULL,
    old_status  VARCHAR(20),            -- NULL on initial creation record
    new_status  VARCHAR(20)  NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_bsh_booking
        FOREIGN KEY (booking_id) REFERENCES booking(id)
        ON DELETE CASCADE,

    INDEX ix_booking_status_history_booking_id (booking_id)
);

CREATE TABLE notification_log (
    id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
    booking_id  BIGINT       NOT NULL,
    event_type  VARCHAR(50)  NOT NULL,  -- e.g. 'booking_created'
    message     TEXT,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_nl_booking
        FOREIGN KEY (booking_id) REFERENCES booking(id)
        ON DELETE CASCADE,

    INDEX ix_notification_log_booking_id (booking_id)
);
```

### `booking_timeline_view`

A read-only MySQL view that joins `booking` with `booking_status_history` to expose a denormalised audit trail. Each row represents one recorded status transition and includes the booking's current details to avoid a second query at read time.

```sql
CREATE VIEW booking_timeline_view AS
SELECT
    b.id             AS booking_id,
    b.passenger_name,
    b.flight_number,
    b.pickup_time,
    b.pickup_location,
    b.dropoff_location,
    b.status         AS current_status,
    h.id             AS history_id,
    h.old_status,
    h.new_status,
    h.created_at     AS transitioned_at
FROM booking b
INNER JOIN booking_status_history h ON h.booking_id = b.id;
```

The view is managed via a manual Alembic migration (`op.execute()`). Alembic's autogenerate is configured with an `include_object` hook to ignore the view so that future `make db-revision` runs do not emit spurious `DROP TABLE` statements.

### Entity Relationship Diagram

```mermaid
erDiagram
    booking {
        bigint id PK
        varchar passenger_name
        varchar flight_number
        datetime pickup_time
        varchar pickup_location
        varchar dropoff_location
        varchar status
        datetime created_at
        datetime updated_at
    }

    booking_status_history {
        bigint id PK
        bigint booking_id FK
        varchar old_status
        varchar new_status
        datetime created_at
    }

    notification_log {
        bigint id PK
        bigint booking_id FK
        varchar event_type
        text message
        datetime created_at
    }

    booking ||--o{ booking_status_history : "has history"
    booking ||--o{ notification_log : "triggers"
```

### Schema decisions

**BIGINT auto-increment (not UUID):** Simpler implementation for a single-service CRUD application. Easier to read, query, and explain. Avoids UUID storage and indexing complexity in MySQL.

**`booking_status_history` table:** `booking.status` stores the current status only. All transitions are recorded in `booking_status_history` with a timestamp. Provides auditability, incident investigation, and lifecycle analysis without bloating the booking row.

**Status as `VARCHAR(20)`, not MySQL `ENUM`:** Adding a status value to a MySQL `ENUM` requires `ALTER TABLE`, which can lock the table. `VARCHAR` avoids DDL changes. Validation is enforced at the application level (Python enum), where it is testable and version-controlled.

**Composite index `(pickup_time, status)`:** The required query is `GET /bookings?date=YYYY-MM-DD`. The leftmost prefix of the index (`pickup_time`) serves this. Operational follow-ups such as filtering by date and status use the full index. One B-tree covers both patterns.

**`flight_number`, `pickup_location`, `dropoff_location` as plain strings:** No separate `flight` or `location` tables. These are booking attributes in current scope. Normalisation would add joins without serving any required use case.

---

## 5. API Design

```
POST   /bookings                   → 201 Created + BookingResponse
GET    /bookings/{id}              → 200 OK     + BookingResponse
PATCH  /bookings/{id}/status       → 200 OK     + BookingResponse
GET    /bookings/{id}/timeline     → 200 OK     + list[BookingTimelineEntryResponse]  # always ≥1 entry
GET    /bookings?date=YYYY-MM-DD   → 200 OK     + list[BookingResponse]
```

#### Timeline endpoint — initial-state guarantee

`GET /bookings/{id}/timeline` always returns at least one entry. `BookingRepository.create()` writes a creation row to `booking_status_history` in the same transaction as the booking itself:

| Field | Value |
|-------|-------|
| `old_status` | `null` — no prior state exists |
| `new_status` | `pending` |
| `transitioned_at` | booking's `created_at` timestamp |

This keeps the history table as the single source of truth for all state changes, including the initial one, and avoids any special-casing in the service layer.

### Request/Response schemas

```python
class BookingCreate(BaseModel):
    passenger_name:   str       # non-empty, max 255
    flight_number:    str       # non-empty, max 20
    pickup_time:      datetime  # ISO 8601
    pickup_location:  str       # non-empty, max 500
    dropoff_location: str       # non-empty, max 500

class BookingStatusUpdate(BaseModel):
    status: BookingStatus       # must be a valid enum value

class BookingResponse(BaseModel):
    id:               int
    passenger_name:   str
    flight_number:    str
    pickup_time:      datetime
    pickup_location:  str
    dropoff_location: str
    status:           BookingStatus
    created_at:       datetime
    updated_at:       datetime

class BookingTimelineEntryResponse(BaseModel):
    booking_id:       int
    passenger_name:   str
    flight_number:    str
    pickup_time:      datetime
    pickup_location:  str
    dropoff_location: str
    current_status:   BookingStatus        # booking's current status
    old_status:       BookingStatus | None  # None for the synthetic creation entry
    new_status:       BookingStatus        # status after this transition
    transitioned_at:  datetime
```

### Error responses

```python
# 404 — booking not found
{"detail": "Booking with id 42 not found"}

# 422 — invalid status transition
{"detail": "Cannot transition from 'completed' to 'pending'"}

# 422 — validation error (Pydantic automatic)
{"detail": [{"loc": ["body", "passenger_name"], "msg": "..."}]}
```

### API design rationale

**`PATCH` for status updates:** Updates a single field, not the full resource. `PUT` implies full replacement, which is semantically incorrect here (RFC 5789).

**Date as query parameter:** `GET /bookings?date=2025-01-15` treats date as a filter on a collection, not a resource identifier. Extensible without URL restructuring (e.g. adding `?status=confirmed` later).

**No pagination in v1:** Daily bookings are bounded by physical capacity (vehicles, drivers, flights). Hundreds of records fit in one response. Premature pagination increases API complexity without solving a real problem.

---

## 6. Status State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING : booking created
    PENDING --> CONFIRMED : confirmed by operations
    PENDING --> CANCELLED : cancelled before confirmation
    CONFIRMED --> COMPLETED : service delivered
    CONFIRMED --> CANCELLED : late cancellation
    COMPLETED --> [*]
    CANCELLED --> [*]
```

**Terminal states:** `completed` and `cancelled` accept no further transitions.

**Enforced in the domain layer, not the database.** Status transition logic is business logic. It belongs where it can be unit-tested, read as code, and changed without DDL migrations. Database triggers or CHECK constraints hide rules in a place that is harder to test and version-control.

The booking is always created with `pending` status. The background task does **not** change status — it only writes a notification log entry. Status changes are always explicit API operations.

---

## 7. Background Notification Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as Application Layer
    participant D as Domain Layer
    participant DB as Database Layer
    participant MySQL as MySQL
    participant I as Integration Layer

    C->>API: POST /bookings
    API->>D: service.create(booking_input)
    D->>DB: repository.create(booking)
    DB->>MySQL: INSERT booking
    MySQL-->>DB: booking row
    DB-->>D: booking domain object
    D-->>API: booking
    API-->>C: 201 + BookingResponse
    Note over API,I: Response sent — background task starts in threadpool
    API->>I: send_notification(booking_id)
    Note over I: Opens its own DB session
    I->>MySQL: INSERT notification_log
```

The HTTP response returns immediately after the booking is persisted. The notification write happens asynchronously in the background. The client never waits for side effects.

The background task opens its own `SessionLocal` session — independent of the request-scoped session that has already committed and closed on the main path.

---

## 8. Testing Strategy

### Unit tests (`tests/unit/`)

Test domain layer behaviour in isolation — no database, no HTTP, no I/O.

`BookingService` receives a `BookingRepository` via constructor injection. In unit tests, this is replaced with a mock/fake. Tests verify business rules only; changing the database tomorrow leaves every unit test unchanged.

| Test | What it validates |
|------|-------------------|
| `test_valid_status_transitions` | All allowed transitions succeed |
| `test_invalid_status_transitions` | Disallowed transitions raise `InvalidStatusTransitionError` |
| `test_create_booking_sets_pending` | New bookings always start as `pending` |

### API tests (`tests/api/`)

Test HTTP-layer concerns: status codes, response shape, input validation, and header behaviour. Use `TestClient` backed by the real test MySQL database (via `db_session` dependency override). `send_notification` is patched to a no-op via an `autouse` fixture so notification side-effects do not leak into HTTP-layer assertions.

### Integration tests (`tests/integration/`)

Test the full request cycle and the repository layer against a real MySQL instance.

**`test_bookings_api.py`** — HTTP → domain → DB round-trip. The 8 tests named in the original Phase 6 spec:

| Test | What it validates |
|------|-------------------|
| `test_create_booking_returns_201` | Full creation flow, response shape, default `pending` status |
| `test_get_booking_by_id` | Retrieval returns correct data |
| `test_pending_to_confirmed` | Valid transition works end-to-end |
| `test_confirmed_to_completed` | Valid transition works end-to-end |
| `test_pending_to_cancelled` | Valid business path exercises full stack |
| `test_invalid_transition_returns_422` | `completed → pending` returns 422 |
| `test_get_nonexistent_booking_returns_404` | Proper error for missing resource |
| `test_list_bookings_by_date` | Date filter returns correct subset |

`send_notification` is suppressed with a module-scoped `autouse` fixture so notification writes do not affect booking assertions.

**`test_booking_repository.py`** — `BookingRepository` directly against MySQL: create, get, update, timeline, history row counts.

**`test_notifications.py`** — `send_notification` called directly; asserts `notification_log` row is written. `SessionLocal` is patched to the test engine.

**`test_create_notification_e2e.py`** — Full wiring test: `POST /bookings` → `BackgroundTasks` → `send_notification` → DB row, no mocks anywhere.

**Isolation strategy:** Row deletion after each test (`SET FOREIGN_KEY_CHECKS=0` + `DELETE` on all tables) keeps the schema intact while guaranteeing data isolation. `READ COMMITTED` isolation (set on all engines) ensures cross-session writes are visible immediately, eliminating fresh-connection workarounds in test assertions.

### Why this split matters

**Unit tests** prove business rules work regardless of infrastructure. They run in milliseconds and serve as executable documentation of domain behaviour.

**Integration tests** prove the full stack works together — SQL queries, HTTP status codes, Pydantic serialisation, and database constraints.

Both are necessary. Unit tests without integration tests miss real-world failures (bad SQL, serialisation bugs). Integration tests without unit tests are slow and make it hard to pinpoint which rule broke.

---

## 9. Docker Compose Setup

```yaml
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: transfer_bookings
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: mysql+pymysql://root:root@db:3306/transfer_bookings
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

**Healthcheck on the database container:** `depends_on` alone waits for the container to start, not for MySQL to accept connections. Without the healthcheck, `alembic upgrade head` fails because the socket is not ready. `service_healthy` solves this reliably.

**Migrations on startup:** `alembic upgrade head` runs before the application starts. The schema is always up-to-date — no manual migration step. Idempotent by design (Alembic tracks applied versions).

**`--reload` flag:** Development only. A production image uses Gunicorn with Uvicorn workers and omits reload.

**`uv` as the package installer:** The `Dockerfile` copies the `uv` binary from the official `ghcr.io/astral-sh/uv` image and uses `uv pip install --system --no-cache` to install dependencies. This replaces bare `pip` and is significantly faster, especially in CI and iterative builds.

---

## 10. Configuration Management

```python
import pydantic_settings

class Settings(pydantic_settings.BaseSettings):
    """
    Application configuration loaded from environment variables.

    Falls back to .env file for local development.
    """
    database_url: str = "mysql+pymysql://root:root@localhost:3306/transfer_bookings"
    debug: bool = False

    class Config:
        env_file = ".env"
```

Type-safe, validated at startup. A missing or malformed `DATABASE_URL` causes an immediate clear error — not a cryptic failure at the first database call. No scattered `os.getenv()` calls across the codebase.

---

## 11. Design Decisions Summary

| Decision | Choice | Reason |
|----------|--------|--------|
| Sync vs async | Sync SQLAlchemy | Simpler, mature drivers, no high-concurrency requirement |
| Background tasks | FastAPI BackgroundTasks | No broker infrastructure for a single side-effect |
| Primary keys | BIGINT auto-increment | Simpler for single-service CRUD, no UUID overhead in MySQL |
| Table naming | Singular (`booking`, `notification_log`, …) | Consistency across DB and Python domain objects |
| Status storage | VARCHAR, not ENUM | No DDL changes when adding statuses |
| Status validation | Domain layer (Python enum + transition map) | Testable, readable, not hidden in DB or triggers |
| Status history | Separate `booking_status_history` table | Auditability and lifecycle analysis without bloating `booking`; creation event always recorded (old_status NULL) |
| Timeline view | MySQL VIEW (`booking_timeline_view`) | Denormalised read model for the audit endpoint; avoids a join in application code; managed by a manual Alembic migration |
| Timeline query | Raw SQL via `sqlalchemy.text()` | VIEW has no ORM model; using raw SQL keeps the ORM metadata clean and prevents autogenerate drift |
| Index | Composite `(pickup_time, status)` | Covers date-only and date+status query patterns with one B-tree |
| Repository pattern | Yes | Isolates ORM from business logic, enables unit testing with mocks |
| Domain vs ORM models | Separate | Prevents ORM session state from leaking into business logic |
| API schemas → domain inputs | Mapped at application boundary | Keeps domain layer free of FastAPI/Pydantic transport concerns |
| Background task session | Own `SessionLocal` | Separate unit of work from the request transaction |
| Session isolation level | `READ COMMITTED` | Each query sees the latest committed data; cross-session writes (e.g. background task) are immediately visible to open test sessions, removing the need for fresh-session workarounds in tests |
| DB for tests | Real MySQL + transaction rollback | Integration tests verify real SQL behaviour, fast cleanup |
| Error handling | Domain exceptions → HTTP codes | Keeps domain framework-agnostic |
| Deployment | Monolithic Docker Compose | Single codebase, two containers, zero external dependencies |
