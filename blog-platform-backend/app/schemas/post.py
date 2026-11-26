from datetime import datetime
from typing import List, Optional, Generic, TypeVar

from pydantic import BaseModel, Field, ConfigDict

from app.models.post import StatusEnum
from app.schemas.user import UserOut
from app.schemas.category import CategoryOut
from app.schemas.tag import TagOut


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    tag_names: List[str] = Field(default_factory=list)  # tags by name; created if they don't exist
    status: StatusEnum = StatusEnum.draft


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    tag_names: Optional[List[str]] = None
    status: Optional[StatusEnum] = None


class PostStatusUpdate(BaseModel):
    status: StatusEnum


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    content: str
    excerpt: Optional[str]
    status: StatusEnum
    view_count: int
    is_archived: bool
    author: UserOut
    category: Optional[CategoryOut]
    tags: List[TagOut]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class PostListItem(BaseModel):
    """Lighter-weight representation used in paginated list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    excerpt: Optional[str]
    status: StatusEnum
    view_count: int
    author: UserOut
    category: Optional[CategoryOut]
    tags: List[TagOut]
    published_at: Optional[datetime]
    created_at: datetime


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[T]
