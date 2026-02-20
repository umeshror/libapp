#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Exec the container's main process (what's set as CMD in Dockerfile)
echo "Starting application..."
exec "$@"
