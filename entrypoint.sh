#!/bin/bash
set -e

if [ "$1" = "uvicorn" ]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete. Starting application..."
fi

exec "$@"
