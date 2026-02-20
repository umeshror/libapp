from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.member import Member
from app.schemas import MemberCreate, MemberResponse


class MemberRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, obj_in: MemberCreate) -> MemberResponse:
        db_obj = Member(name=obj_in.name, email=obj_in.email, phone=obj_in.phone)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return MemberResponse.model_validate(db_obj)

    def get(self, id: UUID) -> Optional[MemberResponse]:
        statement = select(Member).where(Member.id == id)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return MemberResponse.model_validate(result)
        return None

    def get_by_email(self, email: str) -> Optional[MemberResponse]:
        statement = select(Member).where(Member.email == email)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return MemberResponse.model_validate(result)
        return None

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        stmt = select(Member)

        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                (Member.name.ilike(search_term)) | (Member.email.ilike(search_term))
            )

        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        sort_column = getattr(Member, sort_field, Member.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.order_by(Member.id)  # Deterministic

        stmt = stmt.offset(skip).limit(limit)
        results = self.session.execute(stmt).scalars().all()

        return {"items": results, "total": total}
