from typing import Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "minimal": {
        "books": 2000,
        "members": 300,
        "active_borrows": 1000,
        "returned_borrows": 300,
        "overdue_borrows": 15,
    },
    "load_test": {
        "books": 10000,
        "members": 1000,
        "active_borrows": 2000,
        "returned_borrows": 5000,
        "overdue_borrows": 500,
    },
    "scaled_demo": {
        "books": 10000,
        "members": 3000,
        "active_borrows": 5000,
        "returned_borrows": 7000,
        "overdue_borrows": 500,
    },
    "high_scale": {
        "books": 50000,
        "members": 15000,
        "months": 30,
        "target_borrows": 1000000,
    },
}
