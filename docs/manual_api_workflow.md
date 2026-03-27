# Manual API Workflow Guide

Step-by-step walkthrough of the full booking lifecycle using `curl` and `jq`.
All commands target a locally running service. IDs are captured into shell
variables so nothing needs to be copied by hand.

## Table of Contents

- [Prerequisites](#prerequisites)
- [1. Create a booking](#1-create-a-booking)
- [2. Fetch a booking by id](#2-fetch-a-booking-by-id)
- [3. List bookings by date](#3-list-bookings-by-date)
- [4. Confirm a booking](#4-confirm-a-booking)
- [5. Complete a booking](#5-complete-a-booking)
- [6. Cancel a booking](#6-cancel-a-booking)
- [7. Fetch the booking timeline](#7-fetch-the-booking-timeline)
- [8. Attempt an invalid status transition](#8-attempt-an-invalid-status-transition)
- [9. Fetch a non-existent booking](#9-fetch-a-non-existent-booking)
- [10. Full happy-path script](#10-full-happy-path-script)

---

## Prerequisites

- Service running: `make up && make migrate`
- `curl` and `jq` installed locally
- Optional: seed some demo data first — `make seed-demo`

Base URL used throughout: `http://localhost:8000`

---

## 1. Create a booking

```bash
BOOKING=$(curl -s -X POST http://localhost:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "passenger_name": "Ellie Arroway",
    "flight_number":  "VG001",
    "pickup_time":    "2025-09-15T06:30:00",
    "pickup_location":  "Heathrow T5",
    "dropoff_location": "Royal Observatory, Greenwich"
  }')

echo "$BOOKING" | jq .

BOOKING_ID=$(echo "$BOOKING" | jq -r '.id')
echo "Created booking id: $BOOKING_ID"
```

**Expected:** HTTP 201 with the new booking body. `status` will be `"pending"`.

---

## 2. Fetch a booking by id

```bash
curl -s http://localhost:8000/bookings/$BOOKING_ID | jq .
```

**Expected:** HTTP 200 with all booking fields.

---

## 3. List bookings by date

```bash
curl -s "http://localhost:8000/bookings?date=2025-09-15" | jq .
```

**Expected:** HTTP 200 — array of bookings whose `pickup_time` falls on 2025-09-15.
The booking created above should appear in the list.

List a date with no bookings:

```bash
curl -s "http://localhost:8000/bookings?date=2099-01-01" | jq .
```

**Expected:** HTTP 200 — empty array `[]`.

---

## 4. Confirm a booking

```bash
curl -s -X PATCH http://localhost:8000/bookings/$BOOKING_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}' | jq .
```

**Expected:** HTTP 200, `status` is now `"confirmed"`.

---

## 5. Complete a booking

A booking must be `confirmed` before it can be `completed`.

```bash
curl -s -X PATCH http://localhost:8000/bookings/$BOOKING_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}' | jq .
```

**Expected:** HTTP 200, `status` is now `"completed"`.

---

## 6. Cancel a booking

Create a fresh booking to demonstrate cancellation (the one above is already completed):

```bash
CANCEL_ID=$(curl -s -X POST http://localhost:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "passenger_name":   "Alex Kamal",
    "flight_number":    "MC777",
    "pickup_time":      "2025-09-17T16:30:00",
    "pickup_location":  "Gatwick North Terminal",
    "dropoff_location": "Wembley Stadium"
  }' | jq -r '.id')

curl -s -X PATCH http://localhost:8000/bookings/$CANCEL_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "cancelled"}' | jq .
```

**Expected:** HTTP 200, `status` is `"cancelled"`.

---

## 7. Fetch the booking timeline

```bash
curl -s http://localhost:8000/bookings/$BOOKING_ID/timeline | jq .
```

**Expected:** HTTP 200 — array of timeline entries ordered oldest first.
For the booking created in step 1 and driven through confirmed → completed, you will
see three entries:

| `old_status` | `new_status` | meaning              |
|--------------|--------------|----------------------|
| `null`       | `pending`    | creation event       |
| `pending`    | `confirmed`  | step 4 above         |
| `confirmed`  | `completed`  | step 5 above         |

---

## 8. Attempt an invalid status transition

A `completed` booking cannot transition to any other status.

```bash
curl -s -X PATCH http://localhost:8000/bookings/$BOOKING_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "pending"}' | jq .
```

**Expected:** HTTP 422 with a `detail` field describing the disallowed transition:

```json
{
  "detail": "Cannot transition from completed to pending"
}
```

---

## 9. Fetch a non-existent booking

```bash
curl -s http://localhost:8000/bookings/999999 | jq .
```

**Expected:** HTTP 404:

```json
{
  "detail": "Booking 999999 not found"
}
```

---

## 10. Full happy-path script

Copy and paste the block below into a terminal to run the complete workflow
end-to-end in one shot:

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE=http://localhost:8000

echo "── Create booking ──────────────────────────"
B=$(curl -s -X POST $BASE/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "passenger_name":   "Naomi Nagata",
    "flight_number":    "MC042",
    "pickup_time":      "2025-09-16T09:15:00",
    "pickup_location":  "London City Airport",
    "dropoff_location": "Canary Wharf, One Canada Square"
  }')
ID=$(echo "$B" | jq -r '.id')
echo "$B" | jq '{id, status}'

echo "── Confirm ─────────────────────────────────"
curl -s -X PATCH $BASE/bookings/$ID/status \
  -H "Content-Type: application/json" \
  -d '{"status":"confirmed"}' | jq '{id, status}'

echo "── Complete ────────────────────────────────"
curl -s -X PATCH $BASE/bookings/$ID/status \
  -H "Content-Type: application/json" \
  -d '{"status":"completed"}' | jq '{id, status}'

echo "── Timeline ────────────────────────────────"
curl -s $BASE/bookings/$ID/timeline \
  | jq '.[] | {old_status, new_status, transitioned_at}'

echo "── Invalid transition (expect 422) ─────────"
curl -s -X PATCH $BASE/bookings/$ID/status \
  -H "Content-Type: application/json" \
  -d '{"status":"pending"}' | jq .

echo "── Done ────────────────────────────────────"
```
