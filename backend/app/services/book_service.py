from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories.book_repository import BookRepository
from app.schemas import (
    BookCreate,
    BookUpdate,
    BookResponse,
    PaginatedResponse,
    PaginationMeta,
)


class BookService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = BookRepository(session)

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
