from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.user import UserOut


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[int] = None  # set to reply to another comment


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    post_id: int
    parent_id: Optional[int]
    author: UserOut
    created_at: datetime
    updated_at: datetime
    replies: List["CommentOut"] = []


CommentOut.model_rebuild()
