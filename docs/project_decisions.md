# Transfer Booking Service - Project Decisions

## Purpose

This document captures the implementation decisions agreed during project planning. It serves as a working reference before coding starts.

## Naming

- Database tables will use singular names.
- Python domain entities and ORM models will also use singular names.
- We are prioritizing consistency over any particular pluralization convention.

## Core Domain Model

### Main entities

We agreed on three tables:

1. `booking`
2. `notification_log`
3. `booking_status_history`

### Why this shape

- `booking` stores the current state of a transfer booking.
- `notification_log` stores notification-related events triggered around a booking.
- `booking_status_history` stores the history of booking status transitions.

This keeps current state, status audit trail, and notification side effects separated by responsibility.

## Booking Fields

The `booking` table should contain the core booking data:

- `id`
- `passenger_name`
- `flight_number`
- `pickup_time`
- `pickup_location`
- `dropoff_location`
- `status`
- `created_at`
- `updated_at`

## Modeling Decisions

### `flight_number`

- Keep `flight_number` as a plain string field on `booking`.
- Do not model a separate `flight` entity in this project.

Reasoning:

- The assignment does not require flight lifecycle management.
- There is no external flight integration in scope.
- In this service, the flight number is an attribute of the booking rather than a standalone business object.

### `pickup_location` and `dropoff_location`

- Keep both locations as plain string fields on `booking`.
- Do not create a separate `location` table.

Reasoning:

- Locations are simple booking attributes in the current scope.
- Normalizing locations would add joins and complexity without helping required use cases.
- Pickup points may still need free-form operational detail such as terminal, gate, or meeting point.

## ID Strategy

- Use a numeric primary key for `booking`.
- Prefer `BIGINT` style numeric identifiers over UUIDs for this implementation.

Reasoning:

- Simpler implementation for a small CRUD service.
- Easier to explain and maintain in MySQL.
- Avoids extra complexity around UUID storage and indexing.

## Booking Workflow

We agreed on the following statuses:

- `pending`
- `confirmed`
- `completed`
- `cancelled`

### Status meaning

- `pending`: the booking request was created, but not yet operationally confirmed.
- `confirmed`: the booking was accepted and is expected to be fulfilled.
- `completed`: the transfer was actually performed.
- `cancelled`: the booking was cancelled and is terminal.

### Allowed transitions

- `pending -> confirmed`
- `pending -> cancelled`
- `confirmed -> completed`
- `confirmed -> cancelled`

### Important clarification

The background task is not responsible for changing a booking from `pending` to `confirmed`.

The booking must be persisted synchronously during `POST /bookings`, and the background task only handles secondary side effects after the booking has already been created successfully.

## Background Job

### Purpose

The background job exists to demonstrate a post-create side effect that does not belong on the main request path.

### Agreed behavior

- `POST /bookings` creates and persists the booking synchronously.
- After that, a FastAPI background task is triggered.
- That background task writes notification-related event entries to `notification_log`.

### Business interpretation

`notification_log` is treated as a booking-related event or notification history. It represents events such as:

- booking created
- customer confirmation sent
- dispatcher notified
- driver notified

This is a simplified stand-in for real external integrations.

### Scope guidance

- Keep the background workflow simple.
- Do not build a heavy workflow engine.
- If delay simulation is needed for demonstration, keep it very small and avoid long `sleep` values.

## Status History

We explicitly want to preserve the lifecycle of a booking, not only its latest status.

Therefore:

- `booking.status` stores the current status.
- `booking_status_history` stores status changes over time.

Business value:

- auditability
- incident investigation
- lifecycle analysis
- visibility into when a booking entered each state

## Indexing

### Booking

Required indexes:

- primary key on `id`
- index on `pickup_time`

Preferred index choice:

- a composite index on `(pickup_time, status)`

Reasoning:

- The assignment explicitly requires listing bookings by date.
- Operational queries often evolve into date plus status filtering.
- The composite index supports the required query pattern and remains easy to justify.

### Notification log

Required index:

- index on `booking_id`

### Booking status history

Required index:

- index on `booking_id`

Nice-to-have:

- composite index on `(booking_id, created_at)` if we want ordered history reads efficiently.

## Domain Logic Placement

Status transition rules should live in the domain layer.

Implementation direction:

- use a Python enum for booking statuses
- use an explicit transition map
- validate transitions in domain logic
- raise a domain exception for invalid transitions

We do not plan to use a dedicated Python state machine library for this project because the workflow is small and explicit rules are easier to read and test.

## Testing Strategy

### Unit tests

Unit tests should cover pure domain behavior without HTTP or a real database.

Focus areas:

- valid status transitions
- invalid status transitions
- default status on booking creation

### Integration tests

Integration tests should verify the full request cycle through API, domain logic, persistence, and HTTP responses.

Important scenarios:

- create booking returns `201`
- created booking starts in `pending`
- `pending -> confirmed`
- `confirmed -> completed`
- `pending -> cancelled`
- invalid transition returns `422`

An example of a meaningful integration test is creating a booking and then cancelling it directly from `pending`, because that is a valid business path that exercises the full stack.

## Architecture Direction

We plan to follow the layered structure required by the assignment:

- application layer
- domain layer
- integration layer
- database layer

Business rules should stay in the domain layer, request handling in the API layer, persistence in the database layer, and background notification side effects in the integration layer.

## Notes from `docs/claude_architecture.md`

We reviewed the architecture proposal in `docs/claude_architecture.md` and want to preserve several implementation cautions when producing the final architecture.

### API schemas vs domain inputs

We should avoid passing FastAPI or Pydantic request models directly into domain services.

Reasoning:

- the application layer may validate and parse HTTP input
- the domain layer should remain independent from transport-specific DTOs
- if a route handler passes an API schema straight into a service, the domain starts depending on the application layer

Implementation direction:

- map request schemas to domain inputs or command objects at the application boundary
- keep domain services expressed in domain terms rather than FastAPI/Pydantic terms

### Background task database session boundary

The background task should not reuse a request-scoped SQLAlchemy session.

Reasoning:

- the booking is created during the main request transaction
- the background notification write happens after the response path has progressed
- reusing the same session in a background task can create lifecycle and transaction-boundary problems

Implementation direction:

- the background task should open and manage its own database session
- treat notification logging as a separate unit of work from the synchronous booking creation flow

## Session Isolation Level

We configure all SQLAlchemy engines (application and test) to use `READ COMMITTED`.

MySQL's default is `REPEATABLE READ`, which takes a transaction-wide snapshot on the first read. For short-lived CRUD transactions this makes no practical difference to correctness, but it creates a surprising testing inconvenience: a test session that is already open cannot see rows committed by `send_notification`'s separate session, requiring a new connection purely for assertion purposes.

`READ COMMITTED` removes that friction: each SQL statement sees the latest committed data, so an open test session can query rows committed by the background task's session without any extra connection ceremony. It also matches the isolation behaviour that most developers expect by default.

No correctness regression is introduced. The booking service does not rely on repeatable-read snapshot consistency — its transactions are short and do not re-read the same rows mid-transaction.

Applied in:

- `app/database/session.py` — `create_engine(..., isolation_level="READ COMMITTED")`
- `tests/conftest.py` — same flag on the test engine

## Current Scope Principle

When choosing between a simpler field and a normalized entity, we prefer the simpler field unless there is a clear business reason to model a standalone object.

That principle guided these choices:

- no separate `flight` table
- no separate `location` table
- yes to `notification_log`
- yes to `booking_status_history`

## Next Steps

The following items are not required by the current assignment, but are reasonable next steps if the project is extended.

### CI

Potential next step:

- add a simple CI pipeline to run linting, tests, and migration checks automatically on push or pull request

Value:

- gives fast feedback on regressions
- makes test execution more consistent across environments
- documents the expected verification flow for future contributors

### Testcontainers

Potential next step:

- evaluate `testcontainers` for integration tests so test infrastructure can spin up an ephemeral MySQL instance automatically

Value:

- improves test isolation
- reduces manual local setup for fully automated integration runs
- can be especially useful if the project later adds CI-based integration test execution
