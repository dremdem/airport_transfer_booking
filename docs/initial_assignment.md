# BUILD: Transfer Booking Service

Build a small FastAPI application that manages airport transfer bookings — similar in nature to our core business.

## Requirements:

### 1. FastAPI service with the following endpoints:
   - POST /bookings — create a new booking (passenger name, flight number, pickup time, pickup location, dropoff location)
   - GET /bookings/{id} — retrieve a booking by ID
   - PATCH /bookings/{id}/status — update booking status (pending → confirmed → completed / cancelled)
   - GET /bookings?date=YYYY-MM-DD — list all bookings for a given date

### 2. MySQL database via SQLAlchemy
   - Design the schema yourself — we are interested in your modelling decisions
   - Use Alembic for migrations
   - Include at least one index you consider important and explain why in a comment or README

### 3. Background job
   - Implement a simple background task (using FastAPI BackgroundTasks or Celery) that triggers when a booking is created — for example, a simulated notification log entry written to the database

### 4. Tests
   - pytest test suite covering at least the create and status-update flows
   - Show us the distinction between a unit test and an integration test in your suite
   - Aim for meaningful coverage, not 100% padding

### 5. Project structure
   - Use the layered folder structure you described in the interview (application, domain, integration, database layers)
   - Include a short README explaining how to run the project locally with Docker Compose

### Deliverables:
   - A public GitHub repository
   - README with setup instructions and any design decisions worth noting
