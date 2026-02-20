from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.book import Book
from app.schemas import BookCreate, BookUpdate, BookResponse


class BookRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, obj_in: BookCreate) -> BookResponse:
        db_obj = Book(
            title=obj_in.title,
            author=obj_in.author,
            isbn=obj_in.isbn,
            total_copies=obj_in.total_copies,
            available_copies=obj_in.available_copies,
        )
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return BookResponse.model_validate(db_obj)

    def get(self, id: UUID) -> Optional[BookResponse]:
        statement = select(Book).where(Book.id == id)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return BookResponse.model_validate(result)
        return None

    def get_by_isbn(self, isbn: str) -> Optional[BookResponse]:
        statement = select(Book).where(Book.isbn == isbn)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return BookResponse.model_validate(result)
        return None

    def get_with_lock(self, id: UUID) -> Optional[Book]:
        """
        Fetches a book by ID with a row lock (SELECT FOR UPDATE).
        Returns the ORM object directly as it is intended for transactional updates within a service.
        Constraint: Service must handle the session commit.
        """
        statement = select(Book).where(Book.id == id).with_for_update()
        result = self.session.execute(statement).scalar_one_or_none()
        return result

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        """
        Lists books with filtering, sorting, and pagination.
        Returns a dict with items (ORM objects) and total count.
        """
        # Base query
        stmt = select(Book)

        # Filtering (Search)
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                (Book.title.ilike(search_term))
                | (Book.author.ilike(search_term))
                | (Book.isbn.ilike(search_term))
            )

        # Optimization: Get total count before pagination
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        # Sorting
        # Security: sort_field is validated by Service, but we double check or use getattr safe
        # Default to created_at if field not found
        sort_column = getattr(Book, sort_field, Book.created_at)

        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Deterministic secondary sort
        stmt = stmt.order_by(Book.id)

        # Pagination
        stmt = stmt.offset(skip).limit(limit)

        results = self.session.execute(stmt).scalars().all()

        return {"items": results, "total": total}

    def update(self, id: UUID, obj_in: BookUpdate) -> Optional[BookResponse]:
        db_obj = self.session.get(Book, id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return BookResponse.model_validate(db_obj)
