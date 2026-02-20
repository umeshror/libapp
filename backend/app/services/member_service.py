from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories.member_repository import MemberRepository
from app.schemas import MemberCreate, MemberResponse, PaginatedResponse, PaginationMeta


class MemberService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = MemberRepository(session)

    def create_member(self, member_in: MemberCreate) -> MemberResponse:
        return self.repo.create(member_in)

    def get_member(self, member_id: UUID) -> Optional[MemberResponse]:
        return self.repo.get(member_id)

    def get_member_by_email(self, email: str) -> Optional[MemberResponse]:
        return self.repo.get_by_email(email)

    def list_members(
        self,
        offset: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort: str = "-created_at",
    ) -> PaginatedResponse[MemberResponse]:
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        sort_field = sort
        sort_order = "asc"
        if sort.startswith("-"):
            sort_field = sort[1:]
            sort_order = "desc"

        allowed = ["name", "created_at", "email"]
        if sort_field not in allowed:
            raise ValueError(f"Invalid sort field: {sort_field}. Allowed: {allowed}")

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
            data=[MemberResponse.model_validate(m) for m in items],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit) < total,
            ),
        )
