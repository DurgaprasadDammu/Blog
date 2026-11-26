import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    Integer,
    Enum,
    ForeignKey,
    Table,
)
from sqlalchemy.orm import relationship

from app.database import Base


class StatusEnum(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


# Many-to-Many association table between posts and tags
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(280), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(String(500), nullable=True)

    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.draft, index=True)
    view_count = Column(Integer, default=0, nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)  # soft delete
    is_archived = Column(Boolean, default=False, nullable=False)  # archive functionality

    # Foreign Keys — One-to-Many relationships
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    author = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    # Many-to-Many: a post can have many tags, a tag can belong to many posts
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")

    def __repr__(self):
        return f"<Post {self.title} ({self.status})>"
