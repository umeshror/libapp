from dataclasses import dataclass
from typing import Dict


@dataclass
class Metrics:
    borrow_success_count: int = 0
    borrow_failure_count: int = 0
    active_borrows_gauge: int = 0

    def inc_borrow_success(self):
        self.borrow_success_count += 1
        self.active_borrows_gauge += 1

    def inc_borrow_failure(self):
        self.borrow_failure_count += 1

    def dec_active_borrow(self):
        self.active_borrows_gauge = max(0, self.active_borrows_gauge - 1)

    def get_stats(self) -> Dict[str, int]:
        return {
            "borrow_success_count": self.borrow_success_count,
            "borrow_failure_count": self.borrow_failure_count,
            "active_borrows_gauge": self.active_borrows_gauge,
        }


# Singleton instance
metrics = Metrics()
