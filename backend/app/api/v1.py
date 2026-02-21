"""API v1 router — aggregates all domain routers under /api/v1."""

from fastapi import APIRouter
from app.domains.books.router import router as books_router
from app.domains.members.router import router as members_router
from app.domains.borrows.router import router as borrows_router
from app.domains.analytics.router import router as analytics_router
from app.api.seeds import router as seeds_router

v1_router = APIRouter()

v1_router.include_router(books_router, prefix="/books", tags=["books"])
v1_router.include_router(members_router, prefix="/members", tags=["members"])
v1_router.include_router(borrows_router, prefix="/borrows", tags=["borrows"])
v1_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
v1_router.include_router(seeds_router, prefix="/seeds", tags=["seeds"])
