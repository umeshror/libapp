from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int = Field(..., description="Total number of items matching the query")
    limit: int = Field(..., description="Maximum number of items returned")
    offset: int = Field(..., description="Number of items skipped")
    has_more: bool = Field(..., description="Whether there are more items available")


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
