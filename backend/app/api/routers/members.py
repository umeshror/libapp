from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db
from app.services.member_service import MemberService
from app.schemas import MemberCreate, MemberResponse, PaginatedResponse

router = APIRouter()


@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(member_in: MemberCreate, db: Session = Depends(get_db)):
    service = MemberService(db)
    return service.create_member(member_in)


@router.get("/", response_model=PaginatedResponse[MemberResponse])
def list_members(
    offset: int = 0,
    limit: int = 20,
    q: Optional[str] = None,
    sort: str = "-created_at",
    db: Session = Depends(get_db),
):
    service = MemberService(db)
    try:
        return service.list_members(offset=offset, limit=limit, query=q, sort=sort)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# GET /{member_id} removed in favor of app.api.routers.member_details.get_member_core_details
