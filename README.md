# Neighborhood Library Service

## Overview

This project implements a production-minded Library Management Service built to demonstrate clean architecture, data integrity, and scalable design principles.

While the functional scope resembles a typical take-home assignment (books, members, borrowing, returning), the implementation intentionally focuses on:

* Correctness under concurrency
* Clear separation of concerns
* Scalable API modeling
* Realistic data simulation
* Efficient aggregation queries
* Predictable performance at mid-scale

The system supports:

* 50,000 books
* 15,000 members
* ~500,000–1,000,000 borrow records
* 24 months of simulated activity
* Analytics and entity-level insights

This repository is structured to reflect how such a system might evolve in a real-world environment.

---

## Architecture

The service follows a strict layered architecture:

```
Router → Service → Repository → Database
```

### Router Layer

Responsible only for:

* HTTP validation
* Serialization
* Error mapping

No business logic exists in routers.

### Service Layer

Responsible for:

* Business rules
* Transaction management
* Concurrency control
* Input validation

This is where borrowing logic, inventory protection, and invariant enforcement live.

### Repository Layer

Responsible for:

* Database access
* Query optimization
* Aggregation queries
* Pagination mechanics

Repositories never contain business rules.

### Database

The database enforces:

* Referential integrity
* Check constraints
* Indexing
* Transaction isolation

This structure keeps the system maintainable and testable as it grows.

---

## Data Model

### Core Tables

* `books`
* `members`
* `borrow_records`

### Key Decisions

* UUID primary keys
* Database-level constraints
* Indexed time-series fields
* Partial indexes for active borrows
* Deterministic ordering for pagination

### Important Indexes

Borrow records are indexed on:

* `book_id`
* `member_id`
* `borrowed_at`
* `returned_at`
* `due_date`

These indexes ensure that:

* Borrow history queries remain efficient
* Analytics queries scale predictably
* Overdue detection remains fast
* Popularity ranking does not degrade

---

## Borrowing Model & Concurrency

Borrowing operations are fully transactional and concurrency-safe.

The system:

* Uses row-level locking (`SELECT FOR UPDATE`)
* Updates inventory atomically
* Prevents negative inventory
* Enforces borrow limits
* Prevents duplicate active borrows

The goal is simple: correctness first.

Even under concurrent requests, inventory integrity is guaranteed.

---

## API Design

All list endpoints follow a standardized pagination model:

```
GET /resource?limit=20&offset=0&sort=-created_at&q=search
```

Response structure:

```json
{
  "data": [...],
  "meta": {
    "total": 100,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### Why Offset Pagination?

Offset-based pagination was chosen for clarity and simplicity at this scale.
The design intentionally caps page size to prevent unbounded scans.

Cursor-based pagination would be preferable at significantly higher data volumes and is documented as a future enhancement.

---

## Resource Modeling

Heavy nested data is intentionally separated into dedicated endpoints:

```
GET /members/{id}
GET /members/{id}/borrows
GET /members/{id}/analytics

GET /books/{id}
GET /books/{id}/borrows
GET /books/{id}/analytics
```

This avoids:

* Large payload coupling
* Unbounded history responses
* Poor cacheability
* Tight coupling between detail and aggregation data

---

## Analytics

The system includes analytics endpoints that provide:

* Borrow trends (24 months)
* Top books
* Top members
* Overdue bucket distribution
* Inventory utilization ratio
* Member risk segmentation
* Book popularity ranking

All analytics are computed in the database using aggregation queries.
No large dataset is processed in application memory.

This ensures predictable performance even at ~1M borrow records.

---

## Realistic Data Seeding

A large-scale behavioral seeder is included.

It generates:

* 50,000 books
* 15, 000 members
* 30 months of borrow history
* 500k–1M borrow records

### Behavioral Modeling

Books are divided into popularity tiers:

* Highly popular
* Moderate
* Low activity
* Never borrowed

Members are segmented into:

* Heavy readers
* Regular readers
* Casual readers
* Inactive members

The seeder also simulates:

* Seasonal borrow variation
* Overdue probability
* Active borrow distribution
* Inventory consistency validation
* Deterministic random seed

The goal is not random noise, but meaningful analytics patterns.

---

## High-Scale Performance Validation

To verify the system's stability and performance at its maximum design capacity, follow these steps:

1.  **Purge Environment**: Ensure a clean slate by wiping all existing data and containers:
    ```bash
    make docker-down
    ```

2.  **Execute High-Scale Setup**: This performs a "Cold Start" with 50k books, 15k members, and 1M+ records:
    ```bash
    make setup-high
    ```

3.  **Start Services**:
    ```bash
    make start
    ```

4.  **Audit Performance**:
    -   Navigate to the **Dashboard** and verify that 30 months of activity are aggregated within ~2 seconds.
    -   Use the **Global Search** in the Books library to verify sub-500ms response times across 50,000 records.
    -   Check **Book Details** for popular titles to ensure complex history analytics are calculated accurately and instantly.

---

## Performance Considerations

At this scale:

* Bulk inserts are used during seeding
* Session flushing is controlled
* Aggregation queries rely on indexed fields
* Borrow history is always paginated
* N+1 queries are avoided
* Deterministic ordering is enforced

The system is designed to scale predictably without premature optimization.

---

## Quick Start (Local Development)

The easiest way to get started is using the provided `Makefile`.

1.  **Setup Environment**:
    Install dependencies, start the database, and seed initial data:
    ```bash
    make setup
    ```

2.  **Start Services**:
    Launch both backend and frontend servers:
    ```bash
    make start
    ```

3.  **Access**:
    -   Frontend: [http://localhost:3003](http://localhost:3003)
    -   Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Developer Workflow

Use these commands frequently during development to maintain code quality:

| Command | Description |
| :--- | :--- |
| `make test` | Runs the full backend test suite (Pytest + Coverage) |
| `make lint` | Runs full-stack linting (Ruff, Mypy, ESLint) |
| `make format`| Auto-formats backend code using Ruff |
| `make db-fresh` | Resets, Migrates, and Re-seeds the DB (Clean slate) |
| `make db-migration m='msg'` | Generates a new database migration file |
| `make db-shell`| Opens an interactive `psql` shell in the database container |
| `make docker-up`| Starts all services in detached Docker containers |
| `make docker-down`| Stops all services and wipes data volumes |
| `make clean` | Wipes caches and temporary development artifacts |

---

---

## Testing Strategy

Testing focuses on correctness and invariants:

* Unit tests for business rules
* Concurrency tests for borrow operations
* Pagination validation
* Analytics correctness verification
* Seeder distribution constraint checks

Tests prioritize data integrity over superficial endpoint checks.

---

## Scalability & Reliability Roadmap

If this system were to scale further, the following enhancements would be introduced:

### Database

* Partition `borrow_records` by month
* Introduce read replicas for analytics
* Materialized views for heavy aggregations

### API

* Cursor-based pagination
* Short-lived caching layer (Redis)

### Reliability

* Idempotency keys for write operations
* Background job processing
* Observability (metrics + tracing)

The current implementation is intentionally designed to evolve toward these improvements without structural rewrites.

---

## Design Philosophy

This project intentionally avoids unnecessary abstraction and premature optimization.

It prioritizes:

* Correctness under concurrency
* Clean separation of responsibilities
* Predictable performance
* Realistic system behavior
* Clear scaling path

The objective is to demonstrate engineering maturity, not feature volume.

---

## Closing Thoughts

This implementation represents a practical, mid-scale library management system designed with production principles in mind.

It balances:

* Simplicity
* Scalability
* Integrity
* Realism
* Maintainability

The design decisions reflect tradeoffs that would naturally arise in real-world service evolution.
