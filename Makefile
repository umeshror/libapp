# --- Neighborhood Library Makefile ---

.PHONY: help install dev start setup test lint format build db-migrate db-migration db-seed db-reset db-fresh db-seed-high db-shell docker-db docker-up docker-down docker-ps clean

# Help command to list available targets
help:
	@echo "Available commands:"
	@echo "  setup      - Initial setup: install dependencies, migrate, and seed (low volume)"
	@echo "  start      - Ensure DB is up and start dev servers (alias for dev)"
	@echo "  install    - Install both backend and frontend dependencies"
	@echo "  dev        - Start both backend and frontend development servers"
	@echo "  test       - Run backend tests with coverage"
	@echo "  lint       - Run linting and type checking (Backend: Ruff/Mypy, Frontend: Next.js Lint)"
	@echo "  format     - Run auto-formatters (Backend: Ruff)"
	@echo "  build      - Build the frontend production bundle"
	@echo "  db-migrate - Run backend database migrations (Alembic)"
	@echo "  db-migration m='msg' - Create a new database migration"
	@echo "  db-seed    - Populates the database with basic sample data"
	@echo "  db-seed-high - Populates the database with HIGH SCALE sample data (400k+ records)"
	@echo "  db-shell   - Open an interactive PostgreSQL shell"
	@echo "  docker-db  - Starts the PostgreSQL container via docker-compose"
	@echo "  docker-up  - Starts all services via docker-compose"
	@echo "  docker-down - Stops all services and removes data volumes"
	@echo "  docker-ps  - Lists running containers"
	@echo "  clean      - Remove cache files and temporary data"

# Composite Setup
setup: docker-db install db-migrate db-seed
setup-high: docker-db install db-migrate db-seed-high

# Installation
install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

# Development
start: dev

dev:
	@echo "Starting backend on :8000 and frontend on :3003..."
	@# Note: This runs in the foreground. Use Ctrl+C to stop both.
	(cd backend && python -m uvicorn app.main:app --reload --port 8000) & (cd frontend && npm run dev)

# Testing
test:
	cd backend && PYTHONPATH=. pytest --cov=app tests/

# Linting & Static Analysis
lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check app && mypy app --explicit-package-bases

lint-frontend:
	cd frontend && npm run lint

# Formatting
format:
	cd backend && ruff format app tests

# Build
build:
	cd frontend && npm run build

# Database
db-migrate:
	cd backend && alembic upgrade head

db-migration:
	@if [ -z "$(m)" ]; then echo "Error: Please provide a migration message with m='...'. Example: make db-migration m='add_new_table'"; exit 1; fi
	cd backend && alembic revision --autogenerate -m "$(m)"

db-seed:
	cd backend && PYTHONPATH=. python -m app.seeds.seed_runner

db-seed-high:
	cd backend && PYTHONPATH=. python -m app.seeds.seed_runner --scenario high_scale

db-reset:
	cd backend && PYTHONPATH=. python -m app.seeds.reset_db

db-shell:
	docker-compose exec db psql -U user -d library

db-fresh: db-reset db-migrate db-seed

docker-db:
	docker-compose up -d db

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down -v

docker-ps:
	docker-compose ps

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf backend/.coverage
	rm -rf frontend/.next
