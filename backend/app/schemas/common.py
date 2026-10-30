"""Common Pydantic models for responses and errors."""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int = Field(..., description="Total items matching filter")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    has_more: bool = Field(default=False)

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    loc: Optional[List[str]] = None
    msg: str
    type: str


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[List[ErrorDetail]] = None


class MessageResponse(BaseModel):
    message: str
    success: bool = True

