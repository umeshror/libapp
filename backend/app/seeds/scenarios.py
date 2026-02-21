from typing import Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "minimal": {
        "books": 5000,
        "members": 1000,
        "active_borrows": 1000,
        "returned_borrows": 1000,
        "overdue_borrows": 250,
    },
    "load_test": {
        "books": 10000,
        "members": 2000,
        "active_borrows": 2000,
        "returned_borrows": 5000,
        "overdue_borrows": 500,
    },
    "scaled_demo": {
        "books": 50000,
        "members": 5000,
        "active_borrows": 10000,
        "returned_borrows": 14000,
        "overdue_borrows": 1000,
    },
    "high_scale": {
        "books": 200000,
        "members": 60000,
        "months": 120,
        "target_borrows": 4000000,
        "overdue_borrows": 10000
    },
}
