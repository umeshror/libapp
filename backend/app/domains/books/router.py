"""Book domain API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from uuid import UUID
from typing import Optional
from app.shared.deps import get_uow
from app.shared.uow import UnitOfWork
from app.shared.schemas import PaginatedResponse, BulkOperationResponse
from app.domains.books.service import BookService
from fastapi.responses import Response
from fastapi import UploadFile, File
from app.domains.books.schemas import (
    BookCreate, BookUpdate, BookResponse, BookDetailResponse,
)
from app.core.security import rate_limit_dependency

router = APIRouter()


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_dependency)])
def create_book(
    book_in: BookCreate, 
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends(get_uow)
):
    service = BookService(uow, background_tasks)
    return service.create_book(book_in)


@router.get("/", response_model=PaginatedResponse[BookResponse], dependencies=[Depends(rate_limit_dependency)])
def list_books(
    offset: int = 0,
    limit: int = 20,
    q: Optional[str] = None,
    sort: str = "-created_at",
    cursor: Optional[str] = None,
    uow: UnitOfWork = Depends(get_uow),
):
    service = BookService(uow)
    try:
        return service.list_books(
            offset=offset, limit=limit, query=q, sort=sort, cursor=cursor
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    service = BookService(uow)
    book = service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookResponse, dependencies=[Depends(rate_limit_dependency)])
def update_book(
    book_id: UUID, 
    book_in: BookUpdate, 
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends(get_uow)
):
    service = BookService(uow, background_tasks)
    book = service.update_book(book_id, book_in)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.get("/{book_id}/details", response_model=BookDetailResponse)
def get_book_details(
    book_id: UUID,
    history_limit: int = 10,
    history_offset: int = 0,
    uow: UnitOfWork = Depends(get_uow),
):
    """Get comprehensive book details with borrowers, history, and analytics."""
    service = BookService(uow)
    return service.get_book_details(book_id, history_limit, history_offset)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(rate_limit_dependency)])
def delete_book(
    book_id: UUID, 
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends(get_uow)
):
    """Soft delete a book."""
    service = BookService(uow, background_tasks)
    success = service.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found or already deleted")


@router.post("/{book_id}/restore", response_model=BookResponse, dependencies=[Depends(rate_limit_dependency)])
def restore_book(
    book_id: UUID, 
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends(get_uow)
):
    """Restore a soft-deleted book."""
    service = BookService(uow, background_tasks)
    book = service.restore_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found or not deleted")
    return book


@router.get("/export/csv", dependencies=[Depends(rate_limit_dependency)])
def export_books(uow: UnitOfWork = Depends(get_uow)):
    """Export all books to CSV."""
    service = BookService(uow)
    csv_data = service.export_books_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=books.csv"}
    )


@router.post("/import/csv", response_model=BulkOperationResponse, dependencies=[Depends(rate_limit_dependency)])
def import_books(
    file: UploadFile = File(...), 
    uow: UnitOfWork = Depends(get_uow)
):
    """Import books from CSV."""
    service = BookService(uow)
    content = file.file.read()
    return service.import_books_csv(content)
