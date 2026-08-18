#!/bin/bash
set -e

echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

# Execute the CMD passed to this entrypoint (e.g. uvicorn or celery)
exec "$@"
