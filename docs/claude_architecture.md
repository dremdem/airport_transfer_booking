# Transfer Booking Service — Architecture Design

## Context

This document describes the architecture for a **Transfer Booking Service** — a FastAPI application that manages airport transfer bookings (passenger pickups between airports and hotels/destinations).

The service handles the full booking lifecycle: creation, confirmation, completion, and cancellation — with a background notification system and a layered codebase designed for maintainability and testability.

---

## 1. Tech Stack Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | **FastAPI** | Modern, high-performance Python web framework with built-in validation (Pydantic) and OpenAPI docs. |
| ORM | **SQLAlchemy 2.0 (sync)** | See explanation below. |
| Migrations | **Alembic** | The standard migration tool for SQLAlchemy. Versioned, reversible schema changes. |
| DB | **MySQL 8.0** | Widely adopted relational DB. Well-suited for transactional booking data. |
| Background tasks | **FastAPI BackgroundTasks** | See explanation below. |
| Testing | **pytest + httpx** | See explanation below. |
| Containerization | **Docker Compose** | Reproducible local environment with zero manual setup. |

### Why sync SQLAlchemy (not async)

- **Simpler mental model.** Sync code is easier to read, debug, and maintain. No `await` chains, no async session lifecycle gotchas, no risk of accidentally blocking the event loop.
- **Mature driver ecosystem.** Sync MySQL drivers (`PyMySQL`, `mysqlclient`) are battle-tested. Async alternatives (`aiomysql`, `asyncmy`) are less mature and have known edge cases with connection pooling.
- **No concurrency bottleneck.** Transfer bookings are an operational domain — request volumes are bounded by real-world operations (drivers, vehicles, flights). This isn't a high-throughput WebSocket or streaming scenario. A sync threadpool handles the load comfortably.
- **FastAPI handles it natively.** Sync endpoints run in a threadpool automatically — no blocking penalty, no special configuration.

Async would be justified if the service needed to fan out many concurrent I/O calls (e.g., calling 10 external APIs per request). For a CRUD service backed by a single database, sync is the pragmatic choice.

### Why FastAPI BackgroundTasks (not Celery)

- **No additional infrastructure.** Celery requires a message broker (Redis/RabbitMQ) and a separate worker process. For a single notification side-effect, that's significant operational overhead with no proportional benefit.
- **Sufficient for fire-and-forget.** The notification log is a simple DB write that doesn't need retry semantics, task routing, or a result backend.
- **Lower barrier to entry.** Anyone who can read the FastAPI code can understand the background task. Celery introduces its own configuration, serialization quirks, and failure modes.
- **Celery becomes justified when** tasks need reliability guarantees, scheduling, or distributed execution — e.g., sending real SMS/email, calling external payment APIs, or processing heavy batch jobs. At that point, the migration from BackgroundTasks to Celery is straightforward because the integration layer is already isolated.

### Why pytest + httpx (not TestClient alone)

- `httpx.AsyncClient` with `ASGITransport` tests the full ASGI stack without running a server — faster and more reliable than spawning a test server.
- Enables clean separation between unit tests (pure function calls) and integration tests (HTTP → DB round-trip).
- `httpx` is already a transitive FastAPI dependency — no extra install needed.

---

## 2. Layered Architecture

The project follows a four-layer architecture: **application, domain, integration, and database**. Each layer has a single responsibility and communicates only with its immediate neighbors.

```
transfer_booking_service/
├── app/
│   ├── api/                    # APPLICATION LAYER
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── bookings.py     # Route handlers (thin controllers)
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── bookings.py     # Pydantic request/response models
│   │   └── dependencies.py     # FastAPI Depends (DB session, etc.)
│   │
│   ├── domain/                 # DOMAIN LAYER
│   │   ├── __init__.py
│   │   ├── models.py           # Domain entities (plain dataclasses/classes)
│   │   ├── services.py         # Business logic (BookingService)
│   │   ├── exceptions.py       # Domain-specific exceptions
│   │   └── enums.py            # BookingStatus enum, status transitions
│   │
│   ├── integration/            # INTEGRATION LAYER
│   │   ├── __init__.py
│   │   └── notifications.py    # Simulated notification side-effect
│   │
│   ├── database/               # DATABASE LAYER
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy ORM models (table definitions)
│   │   ├── repository.py       # Data access (BookingRepository)
│   │   └── session.py          # Engine, SessionLocal, get_db
│   │
│   ├── config.py               # Pydantic Settings (env-driven config)
│   └── main.py                 # FastAPI app factory
│
├── alembic/
│   ├── versions/               # Migration scripts
│   └── env.py
├── tests/
│   ├── unit/                   # Pure logic tests (no DB, no HTTP)
│   │   ├── __init__.py
│   │   └── test_booking_service.py
│   ├── integration/            # Full-stack tests (HTTP → DB)
│   │   ├── __init__.py
│   │   ├── conftest.py         # Test DB setup, fixtures
│   │   └── test_bookings_api.py
│   └── conftest.py             # Shared fixtures
│
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

### Layer responsibilities and boundaries

#### Application Layer (`app/api/`)

**What it does:** Accepts HTTP requests, validates input via Pydantic schemas, delegates to domain services, formats and returns HTTP responses.

**What it does NOT do:** Contains zero business logic. No status validation, no booking rules, no direct database calls. A route handler is 5–10 lines max.

**Why this boundary matters:** Business logic must be reusable from different entry points — REST API today, but potentially CLI tools, background workers, or internal service calls tomorrow. If logic lives in route handlers, it's locked to HTTP. Keeping routes thin ensures the domain layer is the single source of truth.

```python
# Example: a thin route handler — delegates everything
@router.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = ...,
):
    service = BookingService(BookingRepository(db))
    booking = service.create(payload)
    background_tasks.add_task(send_notification, booking.id)
    return booking
```

#### Domain Layer (`app/domain/`)

**What it does:** Encodes all business rules. Defines what a booking *is*, what status transitions are *legal*, and what invariants must hold.

**Key design decisions:**

- **Status transition validation lives here**, not in the database or API layer. The domain defines the state machine explicitly. Any illegal transition raises a domain exception. This makes the rules testable, readable, and changeable without touching SQL or HTTP code.
- **Domain exceptions** (`BookingNotFoundError`, `InvalidStatusTransitionError`) are raised here and translated to HTTP status codes in the API layer. This keeps the domain layer framework-agnostic — it knows nothing about FastAPI, HTTP, or status codes.
- **BookingStatus as a string-backed Enum** — stored as `VARCHAR` in MySQL, not a MySQL `ENUM` type. String enums are self-documenting in the database, don't break when reordered, and don't require `ALTER TABLE` to add new values.

```python
# Domain status transition rules — explicit and testable
VALID_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING:   {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.COMPLETED, BookingStatus.CANCELLED},
    BookingStatus.COMPLETED: set(),
    BookingStatus.CANCELLED: set(),
}
```

**Separate domain models vs. ORM models:** Domain objects represent business concepts; ORM models represent database rows. Keeping them separate prevents ORM session state (lazy loading, detached instances, identity map behavior) from leaking into business logic. For a small project this is a deliberate architectural demonstration — in production codebases with many tables and cross-service communication, this separation pays off significantly.

#### Integration Layer (`app/integration/`)

**What it does:** Handles side effects that cross system boundaries — external API calls, message queues, third-party services. In this project, it contains a simulated notification that writes a log entry to the database.

**Why it exists as a separate layer:** Side effects (notifications, emails, webhooks) have different failure modes than core business logic. Isolating them behind a clear boundary makes them easy to mock in tests, swap implementations (e.g., replace a log write with a real SMS API), and reason about independently. When the service grows, this layer absorbs new integrations without polluting the domain.

#### Database Layer (`app/database/`)

**What it does:** SQLAlchemy ORM models, the session factory, and the repository pattern.

**Why the Repository pattern:**

- Encapsulates all SQL/ORM queries behind a clean interface (`create`, `get_by_id`, `list_by_date`, `update_status`). The domain layer never writes raw queries.
- Makes unit testing trivial — inject a mock repository, test business logic without a database.
- Provides a natural seam for optimization — you can tune queries, add caching, or switch databases without changing any business logic.

---

## 3. Database Schema Design

```sql
CREATE TABLE bookings (
    id                CHAR(36)     PRIMARY KEY,  -- UUID v4
    passenger_name    VARCHAR(255) NOT NULL,
    flight_number     VARCHAR(20)  NOT NULL,
    pickup_time       DATETIME     NOT NULL,
    pickup_location   VARCHAR(500) NOT NULL,
    dropoff_location  VARCHAR(500) NOT NULL,
    status            VARCHAR(20)  NOT NULL DEFAULT 'pending',
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX ix_bookings_pickup_date_status (pickup_time, status)
);

CREATE TABLE notification_logs (
    id          CHAR(36)    PRIMARY KEY,
    booking_id  CHAR(36)    NOT NULL,
    event_type  VARCHAR(50) NOT NULL,  -- e.g., 'booking_created'
    message     TEXT,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notification_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(id)
        ON DELETE CASCADE,

    INDEX ix_notification_logs_booking_id (booking_id)
);
```

### Schema decisions explained

**UUID primary keys (CHAR(36)) instead of auto-increment integers:**

- UUIDs are generated client-side, so the booking ID is known *before* the database write. This is valuable for background tasks that need the ID immediately and for any future scenario where multiple services write to the same table.
- No coordination required — no sequence locks, no "last insert ID" round-trips. Safe for concurrent inserts from multiple application instances.
- Trade-off acknowledged: UUIDs are larger than integers (36 bytes vs. 4/8 bytes) and cause more InnoDB page splits due to random ordering. For a booking service (thousands to tens of thousands of rows per day), this is negligible. If it ever became a concern, UUID v7 (time-ordered) would solve the fragmentation while preserving the other benefits.

**Status as VARCHAR(20), not MySQL ENUM:**

- Adding a new status value to a MySQL `ENUM` requires `ALTER TABLE`, which can lock the table on large datasets. `VARCHAR` avoids this entirely.
- Validation happens at the application level (Python Enum), where it's testable and explicit. The database stores whatever the application writes — the contract is enforced in code, not in DDL.

**Composite index `ix_bookings_pickup_date_status` on (pickup_time, status):**

- The primary query pattern is `GET /bookings?date=YYYY-MM-DD` — listing bookings by date. This index serves that query directly.
- In operational practice, the most common follow-up is filtering by date *and* status (e.g., "today's confirmed bookings" or "today's pending bookings"). The composite index serves both patterns: date-only queries use the leftmost prefix; date+status queries use the full index.
- This is more useful than indexing each column separately — a single composite index covers the two most important access patterns with one B-tree.

**`created_at` / `updated_at` timestamps:**

- Standard audit columns. `updated_at` with `ON UPDATE CURRENT_TIMESTAMP` is a MySQL-native feature with zero application overhead.
- Essential for debugging — "when was this booking created?" and "when did the status last change?" are the first questions in any incident investigation.

**`notification_logs` as a separate table (not a column on bookings):**

- Models a one-to-many relationship: one booking can trigger multiple notifications over its lifecycle (created, confirmed, completed, cancelled).
- Separating notifications from bookings follows the Single Responsibility Principle at the data level — the bookings table holds booking state, the notification table holds event history. Neither grows columns because of the other.

---

## 4. API Design

```
POST   /bookings                 → 201 Created + BookingResponse
GET    /bookings/{id}            → 200 OK + BookingResponse
PATCH  /bookings/{id}/status     → 200 OK + BookingResponse
GET    /bookings?date=YYYY-MM-DD → 200 OK + list[BookingResponse]
```

### Request/Response schemas

```python
# POST /bookings
class BookingCreate(BaseModel):
    passenger_name: str           # Validated: non-empty, max 255
    flight_number: str            # Validated: non-empty, max 20
    pickup_time: datetime         # ISO 8601
    pickup_location: str          # Validated: non-empty, max 500
    dropoff_location: str         # Validated: non-empty, max 500

# PATCH /bookings/{id}/status
class BookingStatusUpdate(BaseModel):
    status: BookingStatus         # Must be a valid enum value

# Response (all read endpoints)
class BookingResponse(BaseModel):
    id: str
    passenger_name: str
    flight_number: str
    pickup_time: datetime
    pickup_location: str
    dropoff_location: str
    status: BookingStatus
    created_at: datetime
    updated_at: datetime
```

### API design decisions

**PATCH (not PUT) for status updates:** The endpoint updates a single field (status), not the entire resource. PATCH is semantically correct per RFC 5789. PUT implies full resource replacement, which doesn't match the intent.

**Date filter as query parameter (not path):** `GET /bookings?date=2025-01-15` treats the date as a filter on a collection, not as a resource identifier. This is RESTful and extensible — adding `?status=confirmed` or `?page=2` later requires no URL restructuring.

**No pagination in v1:** For a transfer booking service, a single day's bookings are bounded by physical capacity (vehicles, drivers, flights). Hundreds of records fit comfortably in a single response. Pagination would be added when the data model or query patterns outgrow this assumption, but adding it prematurely increases API complexity (cursor vs. offset, total counts, link headers) without solving a real problem.

**Consistent error responses:**

```python
# 404 — booking not found
{"detail": "Booking with id '...' not found"}

# 422 — invalid status transition
{"detail": "Cannot transition from 'completed' to 'pending'"}

# 422 — validation error (Pydantic automatic)
{"detail": [{"loc": ["body", "passenger_name"], "msg": "..."}]}
```

---

## 5. Status State Machine

```
         ┌──────────────┐
         │   PENDING     │
         └──────┬───────┘
                │
        ┌───────┴────────┐
        ▼                ▼
 ┌──────────────┐  ┌──────────────┐
 │  CONFIRMED   │  │  CANCELLED   │
 └──────┬───────┘  └──────────────┘
        │
  ┌─────┴──────┐
  ▼            ▼
┌──────────┐ ┌──────────────┐
│COMPLETED │ │  CANCELLED   │
└──────────┘ └──────────────┘
```

**Valid transitions:**
- `pending → confirmed` — booking accepted by operations
- `pending → cancelled` — cancelled before confirmation
- `confirmed → completed` — service successfully delivered
- `confirmed → cancelled` — late cancellation after confirmation

**Terminal states:** `completed` and `cancelled` allow no further transitions.

**Enforced in the domain layer, not the database.** Status transition logic is business logic. It belongs where it can be unit-tested, read as code, and changed without DDL migrations. Database-level enforcement (triggers, CHECK constraints) hides rules in a place that's harder to test and version-control.

---

## 6. Background Notification Flow

```
Client                API Layer           Domain Layer        Integration Layer     DB
  │                      │                     │                     │               │
  │── POST /bookings ──▶│                     │                     │               │
  │                      │── create() ────────▶│                     │               │
  │                      │                     │── repo.create() ───────────────────▶│
  │                      │                     │◀── booking ────────────────────────│
  │                      │◀── booking ────────│                     │               │
  │                      │                     │                     │               │
  │                      │── background_task ─────────────────────▶│               │
  │◀── 201 + booking ──│                     │                     │               │
  │                      │                     │                     │── log entry ─▶│
  │                      │                     │                     │               │
```

**Key behavior:** The HTTP response returns *immediately* after the booking is persisted. The notification log write happens asynchronously in the background. The client never waits for side effects.

**Why this pattern matters:** In any booking system, the creation response must be fast and reliable. Side effects (notifications, emails, dispatch triggers) should never increase response latency or cause the booking to fail. The background task pattern cleanly separates the critical path (persist booking → return response) from the non-critical path (log notification).

---

## 7. Testing Strategy

### Unit tests (`tests/unit/`)

Test the **domain layer in isolation** — no database, no HTTP, no I/O.

| Test | What it validates |
|------|-------------------|
| `test_valid_status_transitions` | All allowed transitions succeed |
| `test_invalid_status_transitions` | Disallowed transitions raise `InvalidStatusTransitionError` |
| `test_create_booking_sets_pending` | New bookings always start as `pending` |

**How:** The `BookingService` receives a `BookingRepository` via constructor injection. In unit tests, this is replaced with a mock/fake that returns canned data. The tests verify *business logic only* — if the database were swapped for PostgreSQL tomorrow, every unit test would still pass unchanged.

### Integration tests (`tests/integration/`)

Test the **full request cycle**: HTTP → route → service → repository → MySQL → response.

| Test | What it validates |
|------|-------------------|
| `test_create_booking_returns_201` | Full creation flow, response shape, default status |
| `test_get_booking_by_id` | Retrieval returns correct data |
| `test_update_status_valid_transition` | `pending → confirmed` works end-to-end |
| `test_update_status_invalid_transition` | `completed → pending` returns 422 |
| `test_list_bookings_by_date` | Date filter returns correct subset |
| `test_get_nonexistent_booking_returns_404` | Proper error for missing resources |

**How:** Tests run against a real MySQL instance (from Docker Compose). Each test runs inside a database transaction that rolls back after the test — fast execution, full isolation, no cleanup logic.

### Why this split matters

- **Unit tests** prove business rules work *regardless of infrastructure*. They run in milliseconds, need no external services, and serve as executable documentation of domain behavior.
- **Integration tests** prove the entire stack works together — SQL queries return expected results, HTTP status codes are correct, Pydantic serialization round-trips cleanly, and database constraints hold.

Both are necessary. Unit tests without integration tests miss real-world failures (bad SQL, serialization bugs). Integration tests without unit tests are slow and make it hard to pinpoint *which rule* broke.

---

## 8. Docker Compose Setup

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
      sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

### Docker decisions

**Healthcheck on the database container:** `depends_on` alone only waits for the container to *start*, not for MySQL to be *ready to accept connections*. Without a healthcheck, `alembic upgrade head` fails on startup because the database socket isn't open yet. The `service_healthy` condition solves this reliably.

**Alembic migrations run on container startup:** `alembic upgrade head` runs before the application starts. This ensures the schema is always up-to-date — no manual "remember to run migrations" step. Idempotent by design (Alembic tracks applied versions).

**`--reload` flag:** Enables hot-reload during development. A production Dockerfile would omit this and use Gunicorn with Uvicorn workers instead.

---

## 9. Configuration Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:root@localhost:3306/transfer_bookings"
    debug: bool = False

    class Config:
        env_file = ".env"
```

**Why Pydantic Settings:**
- **Type-safe configuration.** Environment variables are parsed and validated at startup. A missing or malformed `DATABASE_URL` causes an immediate, clear error — not a cryptic failure at the first database call.
- **Single source of truth.** No scattered `os.getenv()` calls across the codebase. All config lives in one class, importable anywhere.
- **Environment-first.** Reads from environment variables (12-factor app style), with `.env` file support for local development. No custom config parser needed.

---

## 10. Design Decisions Summary

| Decision | Choice | Key Reason |
|----------|--------|------------|
| Sync vs Async | Sync SQLAlchemy | Simpler, mature drivers, no high-concurrency requirement |
| Background jobs | FastAPI BackgroundTasks | No broker infrastructure for a single side-effect |
| Primary keys | UUID (CHAR 36) | Client-side generation, safe for concurrent/multi-service writes |
| Status storage | VARCHAR, not ENUM | No DDL changes when adding statuses |
| Status validation | Domain layer (Python) | Testable, readable, not hidden in DB triggers |
| Index | Composite (pickup_time, status) | Covers the two primary query patterns with one index |
| Repository pattern | Yes | Isolates ORM from business logic, enables unit testing |
| Domain vs ORM models | Separate | Prevents ORM session state from leaking into business logic |
| DB for tests | Real MySQL + transaction rollback | Integration tests verify real SQL behavior, fast cleanup |
| Error handling | Domain exceptions → HTTP codes | Keeps domain framework-agnostic |
