# Local Development Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Makefile Reference](#makefile-reference)
- [Docker Setup](#docker-setup)
- [Package Management with uv](#package-management-with-uv)
- [Database and Migrations](#database-and-migrations)
- [Running Tests](#running-tests)
- [Project Layout](#project-layout)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Runs the application and database containers |
| Docker Compose | v2 (bundled with Docker Desktop) | Orchestrates multi-container setup |
| GNU Make | any | Shortcut targets for common commands |

No local Python installation is required. All Python tooling runs inside Docker.

---

## Quick Start

```bash
git clone git@github.com:dremdem/airport_transfer_booking.git
cd airport_transfer_booking
cp .env.example .env
make up
```

The service starts at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`.

---

## Environment Variables

All configuration is read from environment variables. Copy `.env.example` to `.env` for local development:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+pymysql://root:root@localhost:3306/transfer_bookings` | SQLAlchemy connection URL |
| `DEBUG` | `false` | Enable debug mode |

In Docker Compose, `DATABASE_URL` is overridden to point at the `db` service:

```
mysql+pymysql://root:root@db:3306/transfer_bookings
```

The `.env` file is read by `app/config.py` via Pydantic Settings and is git-ignored. Never commit real credentials.

---

## Makefile Reference

All commands run inside the Docker container — no local Python or pip needed.

| Target | Command | Description |
|--------|---------|-------------|
| `make up` | `docker compose up --build` | Build and start all services |
| `make down` | `docker compose down` | Stop and remove containers |
| `make test` | `docker compose run --rm app pytest` | Run the full test suite |
| `make lint` | `docker compose run --rm app ruff check .` | Run linter |
| `make migrate` | `docker compose run --rm app alembic upgrade head` | Apply pending migrations |

**Note on `make test` exit codes:** pytest exits with code 5 when no tests are collected (expected during early phases before test files exist). The `make test` target treats exit code 5 as success so the command stays green throughout development.

---

## Docker Setup

### Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| `db` | `mysql:8.0` | `3306` | MySQL database |
| `app` | local build | `8000` | FastAPI application |

### Startup order

The `app` service uses `depends_on: db: condition: service_healthy`. Docker Compose waits for the MySQL healthcheck to pass before starting the application container. This prevents Alembic from attempting to connect before MySQL is ready to accept connections.

The `app` container entrypoint runs:
```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Migrations always run on startup. Alembic is idempotent — already-applied migrations are skipped.

### Volumes

The project directory is mounted into the container at `/app`:
```yaml
volumes:
  - .:/app
```

This enables hot-reload during development: file changes on the host are reflected immediately inside the container without a rebuild.

### Rebuilding after dependency changes

If `requirements.txt` changes, rebuild the image:
```bash
docker compose build --no-cache
```

Or use `make up` which always rebuilds.

---

## Package Management with uv

Dependencies inside the Docker image are installed with [uv](https://github.com/astral-sh/uv), a fast Python package manager written in Rust.

### Why uv

- Significantly faster than `pip` for dependency resolution and installation — typical installs are 10–100× faster
- Drop-in replacement for `pip install` — no new syntax to learn
- Installed directly from the official image layer (`ghcr.io/astral-sh/uv`), no separate install step

### How it is used

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv pip install --system --no-cache -r requirements.txt
```

`--system` installs into the system Python (correct for Docker, avoids a virtual environment inside the container). `--no-cache` keeps the image layer small.

### Adding a new dependency

1. Add the package to `requirements.txt`
2. Rebuild: `docker compose build --no-cache`

uv is only used inside Docker. There is no local virtual environment.

---

## Database and Migrations

### Applying migrations

```bash
make migrate
# or
docker compose run --rm app alembic upgrade head
```

Migrations run automatically on every `make up` / container start, so manual runs are only needed when the app is not running.

### Creating a new migration

```bash
docker compose run --rm app alembic revision --autogenerate -m "describe the change"
```

Alembic compares `app/database/models.py` (the ORM model definitions) against the current database schema and generates a migration script in `alembic/versions/`.

Review the generated file before committing — autogenerate is not always perfect, especially for indexes and constraints.

### Rolling back

```bash
docker compose run --rm app alembic downgrade -1
```

---

## Running Tests

```bash
make test
# or
docker compose run --rm app pytest
```

### Test layout

```
tests/
├── unit/                        # Pure domain logic — no DB, no HTTP, runs in milliseconds
│   └── test_booking_service.py  # Status transitions, default status, BookingService rules
└── integration/                 # Full HTTP → DB round-trip — requires the db container
```

Unit tests have no external dependencies and run in under a second. Integration tests require the `db` container (started automatically via `depends_on`).

### Running only unit tests

```bash
docker compose run --rm app pytest tests/unit/ -v
```

### Running a specific test file

```bash
docker compose run --rm app pytest tests/unit/test_booking_service.py -v
```

### Running with verbose output

```bash
make test
# expands to: docker compose run --rm app pytest || [ $? -eq 5 ]
```

---

## Project Layout

```
airport_transfer_booking/
├── app/
│   ├── api/            # Application layer — routes, schemas, dependencies
│   ├── domain/         # Domain layer — business rules, entities, exceptions
│   ├── integration/    # Integration layer — notification side-effects
│   ├── database/       # Database layer — ORM models, session, repository
│   ├── config.py       # Pydantic Settings (env-driven)
│   └── main.py         # FastAPI app factory
├── alembic/            # Migration environment and version scripts
├── docs/               # Project documentation
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── .env.example        # Environment variable template
├── docker-compose.yml  # Local orchestration
├── Dockerfile          # Application image (uv + Python 3.12)
├── Makefile            # Developer shortcuts
├── pytest.ini          # Test configuration
└── requirements.txt    # Python dependencies
```
