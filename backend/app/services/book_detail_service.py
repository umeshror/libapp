from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.book_detail_repository import BookDetailRepository
from app.schemas.book_details import BookDetailResponse, BorrowHistoryResponse
from app.schemas import BookResponse


class BookDetailService:
    def __init__(self, session: Session):
        self.repository = BookDetailRepository(session)

    def get_book_details(
        self, book_id: UUID, history_limit: int = 10, history_offset: int = 0
    ) -> BookDetailResponse:
        # 1. Fetch Core Book Details
        book = self.repository.get_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # 2. Fetch Current Borrowers
        current_borrowers = self.repository.get_current_borrowers(book_id)

        # 3. Fetch Borrow History (Paginated)
        history_items, total_history = self.repository.get_borrow_history(
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
        analytics = self.repository.get_analytics(book_id, book)

        return BookDetailResponse(
            book=BookResponse.model_validate(book),
            current_borrowers=current_borrowers,
            borrow_history=borrow_history,
            analytics=analytics,
        )
