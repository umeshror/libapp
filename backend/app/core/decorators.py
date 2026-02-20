import time
import functools
import random
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import StaleDataError
from app.core.logging import logger


def db_retry(max_retries=3, base_delay=0.1, max_delay=1.0):
    """
    Decorator to retry database operations on OperationalError (e.g., deadlocks)
    or StaleDataError (Optimistic Locking).
    Uses exponential backoff with jitter.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (OperationalError, StaleDataError) as e:
                    # Rollback session if it exists on self (args[0])
                    if args and hasattr(args[0], "session"):
                        try:
                            args[0].session.rollback()
                        except Exception:
                            pass

                    if retries >= max_retries:
                        logger.error(
                            f"Max retries reached for {func.__name__} due to: {e}"
                        )
                        raise e

                    retries += 1
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    jitter = random.uniform(0, 0.1 * delay)
                    sleep_time = delay + jitter

                    logger.warning(
                        f"Database error in {func.__name__}: {e}. Retrying ({retries}/{max_retries}) in {sleep_time:.4f}s"
                    )
                    time.sleep(sleep_time)

        return wrapper

    return decorator


def measure_borrow_metrics(func):
    """Decorator to measure borrow success/failure."""
    from app.core.metrics import metrics

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if func.__name__ == "borrow_book":
                metrics.inc_borrow_success()
            elif func.__name__ == "return_book":
                metrics.dec_active_borrow()
            return result
        except Exception as e:
            if func.__name__ == "borrow_book":
                metrics.inc_borrow_failure()
            raise e

    return wrapper
