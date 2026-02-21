#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Database Seeding Logic
if [ "$SEED_DATA" = "true" ]; then
    echo "Force seeding enabled (SEED_DATA=true). Clearing and seeding with scenario: ${SEED_SCENARIO:-minimal}..."
    python app/seeds/seed_runner.py --scenario ${SEED_SCENARIO:-minimal} --clear
else
    echo "Checking if database needs initial seeding (SEED_DATA is false/unset)..."
    python app/seeds/seed_runner.py --scenario ${SEED_SCENARIO:-minimal} --if-empty
fi

# Exec the container's main process
echo "Starting application..."
exec "$@"
