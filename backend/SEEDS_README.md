
## Development Seeding

The application includes a production-grade seeder located in `app/seeds/`.

### How to Run

1.  **Via Docker (On Startup)**:
    Set the `SEED_SCENARIO` environment variable in `docker-compose.yml` or your `.env` file.
    ```bash
    SEED_SCENARIO=minimal docker-compose up
    ```

2.  **Via CLI (Manual)**:
    ```bash
    docker exec libapp-api-1 python -m app.seeds.seed_runner --scenario minimal
    ```

### Available Scenarios (`app/seeds/scenarios.py`)

-   **minimal**: 2000 books, 300 members, ~500 borrow records. Good for local dev.
-   **load_test**: 10k books, 1k members, ~7.5k borrows. Good for performance testing.

### Features

-   **Idempotent**: Safe to run multiple times. Checks for existing data before inserting.
-   **Service Layer**: Uses the actual application constraints and logic.
-   **Production Protection**: Will refuse to run if `ENVIRONMENT=production`.
