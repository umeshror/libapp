from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.repositories.book_repository import BookRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas import (
    BookCreate,
    BookUpdate,
    BookResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.schemas.book_details import BookDetailResponse, BorrowHistoryResponse


class BookService:
    """Orchestrates book operations with input validation and analytics aggregation."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = BookRepository(session)
        self.analytics_repo = AnalyticsRepository(session)

    def create_book(self, book_in: BookCreate) -> BookResponse:
        return self.repo.create(book_in)

    def get_book(self, book_id: UUID) -> Optional[BookResponse]:
        return self.repo.get(book_id)

    def get_book_by_isbn(self, isbn: str) -> Optional[BookResponse]:
        return self.repo.get_by_isbn(isbn)

    def list_books(
        self,
        offset: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort: str = "-created_at",
    ) -> PaginatedResponse[BookResponse]:
        """List books with validated pagination, search, and sort parameters."""
        # Validate limit
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        # Parse sort
        sort_field = sort
        sort_order = "asc"
        if sort.startswith("-"):
            sort_field = sort[1:]
            sort_order = "desc"

        # Validate sort field
        allowed_sort_fields = ["title", "author", "available_copies", "created_at"]
        if sort_field not in allowed_sort_fields:
            raise ValueError(
                f"Invalid sort field: {sort_field}. Allowed: {allowed_sort_fields}"
            )

        # Call Repo
        result = self.repo.list(
            skip=offset,
            limit=limit,
            query=query,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        items = result["items"]
        total = result["total"]

        return PaginatedResponse(
            data=[BookResponse.model_validate(book) for book in items],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit) < total,
            ),
        )

    def update_book(self, book_id: UUID, book_in: BookUpdate) -> Optional[BookResponse]:
        return self.repo.update(book_id, book_in)

    def get_book_details(
        self, book_id: UUID, history_limit: int = 10, history_offset: int = 0
    ) -> BookDetailResponse:
        """Aggregate book info, active borrowers, paginated history, and analytics."""
        # 1. Fetch Core Book Details
        book = self.repo.get_with_lock(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # 2. Fetch Current Borrowers
        current_borrowers = self.repo.get_current_borrowers(book_id)

        # 3. Fetch Borrow History (Paginated)
        history_items, total_history = self.repo.get_borrow_history(
            book_id, history_limit, history_offset
        )

        borrow_history = BorrowHistoryResponse(
            data=history_items,
            meta={
                "total": total_history,
                "limit": history_limit,
                "offset": history_offset,
                "has_more": (history_offset + history_limit) < total_history,
            },
        )

        # 4. Fetch Analytics
        analytics = self.analytics_repo.get_book_analytics(book_id, book)

        return BookDetailResponse(
            book=BookResponse.model_validate(book),
            current_borrowers=current_borrowers,
            borrow_history=borrow_history,
            analytics=analytics,
        )
