"""FastAPI dependency providers."""

from typing import Generator
from app.shared.uow import UnitOfWork


def get_uow() -> Generator[UnitOfWork, None, None]:
    """Yield a UnitOfWork and ensure its session is closed after the request."""
    uow = UnitOfWork()
    with uow:
        yield uow
