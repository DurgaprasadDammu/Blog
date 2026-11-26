import uuid
from datetime import datetime

# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, DateTime, Integer
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship

from app.database import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    slug = Column(String(70), unique=True, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Many-to-Many: tags <-> posts (via post_tags association table defined in post.py)
    posts = relationship("Post", secondary="post_tags", back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.name}>"
