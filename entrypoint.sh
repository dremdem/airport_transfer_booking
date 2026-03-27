#!/bin/bash
set -e

if [ "$1" = "uvicorn" ]; then
    echo "Waiting for database to be reachable..."
    for i in $(seq 1 30); do
        alembic upgrade head && break
        echo "  attempt $i/30 failed, retrying in 2s..."
        sleep 2
    done
    echo "Migrations complete. Starting application..."
fi

exec "$@"
