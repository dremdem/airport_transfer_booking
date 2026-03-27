# Airport Transfer Booking Service

A REST API for managing airport transfer bookings — built with FastAPI, SQLAlchemy, MySQL, and Docker Compose. Includes an optional React + TypeScript SPA frontend.

## Table of Contents

- [Quick Start](#quick-start)
- [Frontend](#frontend)
- [Running Tests](#running-tests)
- [Running Migrations](#running-migrations)
- [Makefile Reference](#makefile-reference)
- [Project Structure](#project-structure)
- [Design Decisions](#design-decisions)

---

## Quick Start

**Prerequisites:** Docker and Docker Compose.

```bash
git clone https://github.com/dremdem/airport_transfer_booking.git
cd airport_transfer_booking
make up
make migrate
```

The API is now available at <http://localhost:8000>.

Interactive docs (Swagger UI): <http://localhost:8000/docs>

### Environment variables

`docker-compose.yml` already sets the required environment variables directly, so no `.env` file is needed to run the stack with Docker Compose.

`.env.example` documents the available settings for reference or local overrides:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+pymysql://root:root@db:3306/transfer_bookings` | Live database connection (`db` resolves inside the Compose network) |
| `TEST_DATABASE_URL` | `mysql+pymysql://root:root@db:3306/transfer_bookings_test` | Isolated test database |
| `DEBUG` | `false` | Enable debug mode |

> **Note:** The hostname `db` only resolves from inside the Docker Compose network. If you run the app outside Docker (e.g. a local virtual environment), replace `db` with `localhost`.

---

## Frontend

A minimal SPA (React + TypeScript + Vite) lives in `frontend/`. It covers all booking flows: create, list by date, booking details, timeline, and status updates.

**Prerequisites:** Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The dev server proxies `/api` requests to `http://localhost:8000`, so the backend must be running (`make up && make migrate`).

```bash
# Production build
npm run build
```

---

## Running Tests

```bash
make test
```

This runs the full test suite (unit + integration + API) inside Docker against a real MySQL instance. All tests run against the `transfer_bookings_test` database, which is created automatically on first container start.

```bash
# Run a specific test file
docker compose run --rm app pytest tests/integration/test_bookings_api.py -v
```

---

## Running Migrations

```bash
# Apply all pending migrations
make migrate

# Create a new migration from ORM changes
make db-revision MSG="add column xyz"

# Downgrade all migrations (wipes the schema)
make db-reset
```

---

## Makefile Reference

| Target | Description |
|--------|-------------|
| `make help` | Show all available targets |
| `make build` | Rebuild the Docker image |
| `make up` | Start all services in the background |
| `make down` | Stop and remove containers |
| `make migrate` | Apply pending Alembic migrations |
| `make test` | Run the full test suite |
| `make lint` | Run the ruff linter |
| `make format` | Run the ruff formatter |
| `make check` | Alias for `make lint` — run all code quality checks |
| `make db-revision MSG="..."` | Generate a new migration |
| `make db-reset` | Downgrade all migrations |
| `make db-connect` | Open an interactive MySQL shell |

---

## Project Structure

```
airport_transfer_booking/
├── app/
│   ├── api/              # HTTP layer: route handlers, Pydantic schemas, dependencies
│   ├── domain/           # Business logic: BookingService, status state machine, exceptions
│   ├── integration/      # Side effects: send_notification background task
│   ├── database/         # Persistence: ORM models, BookingRepository, session factory
│   ├── config.py         # Environment-driven settings (Pydantic Settings)
│   └── main.py           # FastAPI app factory
├── alembic/              # Database migrations
├── tests/
│   ├── unit/             # Domain logic tests — no DB, no HTTP
│   ├── api/              # HTTP contract tests — status codes, validation, response shape
│   └── integration/      # Full-stack tests — route → service → repository → MySQL
├── docker/
│   └── init.sql          # Creates transfer_bookings_test schema on first container start
├── docker-compose.yml
├── Dockerfile
└── Makefile
```

### Layer responsibilities

| Layer | Package | Responsibility |
|-------|---------|----------------|
| API | `app/api/` | Accept HTTP, validate input, delegate to domain, format response |
| Domain | `app/domain/` | Business rules, status transitions, domain exceptions |
| Integration | `app/integration/` | Notification side-effects (background task) |
| Database | `app/database/` | ORM models, repository, session management |

---

## Design Decisions

### Synchronous SQLAlchemy over async

The booking service is a straightforward CRUD application. Synchronous SQLAlchemy with FastAPI's threadpool is simpler to reason about, easier to test, and avoids the complexity of async SQLAlchemy session management. There is no high-concurrency bottleneck that would justify the added complexity.

### FastAPI `BackgroundTasks` over Celery

A single notification side-effect does not justify adding Redis or RabbitMQ to the infrastructure. `BackgroundTasks` runs the task in the same process after the response is sent, with zero extra dependencies. If the notification volume grows or reliability guarantees are needed, the integration layer can be swapped for Celery without touching the domain or API layers.

### `BIGINT` auto-increment over UUID

Simpler implementation for a single-service application. Easier to read in logs and queries. Avoids UUID storage and index fragmentation complexity in MySQL. UUIDs would be the right choice for distributed ID generation across multiple services.

### Composite index `(pickup_time, status)`

The primary query pattern is "bookings on a given date" (`GET /bookings?date=YYYY-MM-DD`). A composite index on `(pickup_time, status)` covers both date-only and date+status query patterns with a single B-tree, without a full table scan.

### `booking_status_history` as a separate table

Storing every status transition in a dedicated table provides a complete, immutable audit trail without bloating the `booking` row. The creation event (old_status `NULL`, new_status `pending`) is written atomically with the booking insert, so the timeline always has at least one entry. Status validation lives in the domain layer (Python enum + transition map), not in database triggers or constraints, keeping the rules testable and readable.

### `READ COMMITTED` session isolation

MySQL defaults to `REPEATABLE READ`, which takes a transaction-wide snapshot on the first read. For this project's short-lived CRUD transactions that default causes surprising testing behaviour: an open test session cannot see rows committed by the background task's separate session without opening a fresh connection. `READ COMMITTED` makes every SQL statement see the latest committed data, which matches developer expectations and simplifies cross-session test assertions.

### MySQL VIEW for timeline queries

`booking_timeline_view` joins `booking` and `booking_status_history` into a flat denormalised read model for the `GET /bookings/{id}/timeline` endpoint. The view is defined in a manual Alembic migration and queried via raw SQL (`sqlalchemy.text()`), keeping the ORM metadata clean and preventing autogenerate drift.
