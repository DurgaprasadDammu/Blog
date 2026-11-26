import uuid
from datetime import datetime

# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship, backref

from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content = Column(Text, nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)  # soft delete

    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Self-referential FK for nested replies (One-to-Many: comment -> replies)
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")

    # Self-referential relationship for nested replies (a comment can have many child replies)
    replies = relationship(
        "Comment",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        single_parent=True,
    )

    def __repr__(self):
        return f"<Comment {self.id} on Post {self.post_id}>"
