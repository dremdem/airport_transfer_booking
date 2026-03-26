"""FastAPI application factory for the Transfer Booking Service."""

import fastapi

app = fastapi.FastAPI(
    title="Transfer Booking Service",
    description="Airport transfer booking management API.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict:
    """
    Health check endpoint.

    :return: dict with service status
    """
    return {"status": "ok"}
