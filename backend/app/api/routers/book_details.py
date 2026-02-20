from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps import get_db
from app.services.book_detail_service import BookDetailService
from app.schemas.book_details import BookDetailResponse

router = APIRouter()


@router.get("/{book_id}/details", response_model=BookDetailResponse)
def get_book_details(
    book_id: UUID,
    history_limit: int = 10,
    history_offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Get comprehensive book details including:
    - Core metadata
    - Current active borrowers
    - Paginated borrow history
    - Analytics and insights
    """
    service = BookDetailService(db)
    return service.get_book_details(book_id, history_limit, history_offset)
