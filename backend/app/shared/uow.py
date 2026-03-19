from abc import ABC, abstractmethod
from typing import Type, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

from app.domains.books.repository import BookRepository
from app.domains.members.repository import MemberRepository
from app.domains.borrows.repository import BorrowRepository
from app.domains.analytics.repository import AnalyticsRepository


class AbstractUnitOfWork(ABC):
    """Abstract base class for the Unit of Work pattern."""
    books: BookRepository
    members: MemberRepository
    borrows: BorrowRepository
    analytics: AnalyticsRepository
    session: Session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()

    @abstractmethod
    def commit(self):
        raise NotImplementedError

    @abstractmethod
    def rollback(self):
        raise NotImplementedError
    
    @abstractmethod
    def flush(self):
        raise NotImplementedError


class UnitOfWork(AbstractUnitOfWork):
    """
    Concrete implementation of Unit of Work using SQLAlchemy.
    Supports reentrancy to allow nested context managers to share the same session.
    """
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self.session: Optional[Session] = None
        self._nested_count = 0

    def __enter__(self):
        if self._nested_count == 0:
            self.session = self.session_factory()
            self.books = BookRepository(self.session)
            self.members = MemberRepository(self.session)
            self.borrows = BorrowRepository(self.session)
            self.analytics = AnalyticsRepository(self.session)
        self._nested_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._nested_count -= 1
        if self._nested_count == 0:
            try:
                if exc_type is not None:
                    self.rollback()
            finally:
                if self.session:
                    self.session.close()
        elif exc_type is not None:
            self.rollback()

    def commit(self):
        if self.session:
            self.session.commit()

    def rollback(self):
        if self.session:
            self.session.rollback()
        
    def flush(self):
        if self.session:
            self.session.flush()
    
    def refresh(self, obj):
        if self.session:
            self.session.refresh(obj)
