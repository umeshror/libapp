"""Book domain service — orchestrates book operations with explicit Unit of Work management."""

from typing import Optional, List
from uuid import UUID
from fastapi import BackgroundTasks
from app.shared.uow import AbstractUnitOfWork
from app.shared.audit import log_audit_event
from app.shared.csv_utils import parse_csv_stream, generate_csv_response
from app.shared.schemas import PaginatedResponse, PaginationMeta, BulkOperationResponse
from app.domains.books.schemas import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookDetailResponse,
    BorrowHistoryResponse,
)
from app.core.exceptions import BookNotFoundError


class BookService:
    """Orchestrates book operations with explicit Unit of Work management."""

    def __init__(self, uow: AbstractUnitOfWork, background_tasks: Optional[BackgroundTasks] = None):
        self.uow = uow
        self.background_tasks = background_tasks

    def create_book(self, book_in: BookCreate) -> BookResponse:
        with self.uow:
            book = self.uow.books.create(book_in)
            self.uow.commit()
            self.uow.refresh(book)
            
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event, 
                    self.uow.session, 
                    "BOOK_CREATE", 
                    str(book.id), 
                    f"Created book: {book.title}"
                )
            return BookResponse.model_validate(book)

    def get_book(self, book_id: UUID) -> Optional[BookResponse]:
        with self.uow:
            book = self.uow.books.get(book_id)
            return BookResponse.model_validate(book) if book else None

    def get_book_by_isbn(self, isbn: str) -> Optional[BookResponse]:
        with self.uow:
            book = self.uow.books.get_by_isbn(isbn)
            return BookResponse.model_validate(book) if book else None

    def list_books(
        self,
        offset: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort: str = "-created_at",
        cursor: Optional[str] = None,
    ) -> PaginatedResponse[BookResponse]:
        """List books with validated pagination, search, and sort parameters."""
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        sort_field = sort
        sort_order = "asc"
        if sort.startswith("-"):
            sort_field = sort[1:]
            sort_order = "desc"

        allowed_sort_fields = ["title", "author", "available_copies", "created_at"]
        if sort_field not in allowed_sort_fields:
            raise ValueError(
                f"Invalid sort field: {sort_field}. Allowed: {allowed_sort_fields}"
            )

        with self.uow:
            result = self.uow.books.list(
                skip=offset,
                limit=limit,
                query=query,
                sort_field=sort_field,
                sort_order=sort_order,
                cursor=cursor,
            )

        items = result["items"]
        total = result["total"]
        next_cursor = result.get("next_cursor")

        return PaginatedResponse(
            data=[BookResponse.model_validate(book) for book in items],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=next_cursor is not None if cursor else (offset + limit) < total,
                next_cursor=next_cursor,
            ),
        )

    def update_book(self, book_id: UUID, book_in: BookUpdate) -> Optional[BookResponse]:
        with self.uow:
            book = self.uow.books.update(book_id, book_in)
            if not book:
                return None
            self.uow.commit()
            self.uow.refresh(book)
            
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event,
                    self.uow.session,
                    "BOOK_UPDATE",
                    str(book.id),
                    f"Updated book: {book.title}"
                )
            return BookResponse.model_validate(book)

    def delete_book(self, book_id: UUID) -> bool:
        with self.uow:
            success = self.uow.books.delete(book_id)
            if success:
                self.uow.commit()
                if self.background_tasks:
                    self.background_tasks.add_task(
                        log_audit_event,
                        self.uow.session,
                        "BOOK_DELETE",
                        str(book_id),
                        f"Deleted book {book_id}"
                    )
            return success

    def restore_book(self, book_id: UUID) -> Optional[BookResponse]:
        with self.uow:
            book = self.uow.books.restore(book_id)
            if not book:
                return None
            self.uow.commit()
            self.uow.refresh(book)
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event,
                    self.uow.session,
                    "BOOK_RESTORE",
                    str(book.id),
                    f"Restored book {book.title}"
                )
            return BookResponse.model_validate(book)

    def export_books_csv(self) -> str:
        with self.uow:
            books = self.uow.books.list_all()
        data = [BookResponse.model_validate(b).model_dump(mode="json") for b in books]
        fieldnames = ["id", "title", "author", "isbn", "total_copies", "available_copies", "created_at", "updated_at"]
        return generate_csv_response(data, fieldnames)

    def import_books_csv(self, file_content: bytes) -> BulkOperationResponse:
        rows = parse_csv_stream(file_content)
        books_in = []
        for row in rows:
            try:
                books_in.append(BookCreate(
                    title=row["title"],
                    author=row["author"],
                    isbn=row["isbn"],
                    total_copies=int(row.get("total_copies", 1))
                ))
            except Exception:
                continue

        with self.uow:
            success, failed, errors = self.uow.books.bulk_create(books_in)
            self.uow.commit()
            
        return BulkOperationResponse(
            total_records=len(rows),
            successful=success,
            failed=failed + (len(rows) - len(books_in) - success),
            errors=errors
        )

    def get_book_details(
        self, book_id: UUID, history_limit: int = 10, history_offset: int = 0
    ) -> BookDetailResponse:
        """Aggregate book info, active borrowers, paginated history, and analytics."""
        with self.uow:
            book = self.uow.books.get_with_lock(book_id)
            if not book:
                raise BookNotFoundError("Book not found.")

            current_borrowers = self.uow.books.get_current_borrowers(book_id)

            history_items, total_history = self.uow.books.get_borrow_history(
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

            analytics = self.uow.analytics.get_book_analytics(book_id, book)

        return BookDetailResponse(
            book=BookResponse.model_validate(book),
            current_borrowers=current_borrowers,
            borrow_history=borrow_history,
            analytics=analytics,
        )
