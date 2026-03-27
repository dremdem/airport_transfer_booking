"""FastAPI application factory for the Transfer Booking Service."""

import fastapi
import fastapi.middleware.cors
import fastapi.responses

import app.api.routes.bookings as bookings_routes
import app.domain.exceptions as exceptions


app = fastapi.FastAPI(
    title="Transfer Booking Service",
    description="Airport transfer booking management API.",
    version="0.1.0",
)

app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bookings_routes.router)


@app.exception_handler(exceptions.BookingNotFoundError)
async def booking_not_found_handler(
    request: fastapi.Request,
    exc: exceptions.BookingNotFoundError,
) -> fastapi.responses.JSONResponse:
    """
    Translate ``BookingNotFoundError`` to an HTTP 404 response.

    :param request: incoming FastAPI request (required by the handler signature)
    :param exc: the domain exception carrying the missing booking id
    :return: JSON 404 response with error detail
    """
    return fastapi.responses.JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(exceptions.InvalidStatusTransitionError)
async def invalid_transition_handler(
    request: fastapi.Request,
    exc: exceptions.InvalidStatusTransitionError,
) -> fastapi.responses.JSONResponse:
    """
    Translate ``InvalidStatusTransitionError`` to an HTTP 422 response.

    :param request: incoming FastAPI request (required by the handler signature)
    :param exc: the domain exception describing the disallowed transition
    :return: JSON 422 response with error detail
    """
    return fastapi.responses.JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.get("/health")
def health_check() -> dict:
    """
    Health check endpoint.

    :return: dict with service status
    """
    return {"status": "ok"}
