from typing import Optional

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload

from app.models.comment import Comment
from app.schemas.comment import CommentCreate


def get_comment(db: Session, comment_id: int) -> Optional[Comment]:
    return (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.id == comment_id, Comment.is_deleted == False)  # noqa: E712
        .first()
    )


def create_comment(db: Session, comment_in: CommentCreate, post_id: int, author_id: int) -> Comment:
    db_comment = Comment(
        content=comment_in.content,
        post_id=post_id,
        author_id=author_id,
        parent_id=comment_in.parent_id,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def list_top_level_comments_for_post(db: Session, post_id: int):
    """Returns only top-level comments (no parent). Nested replies are loaded
    via the `replies` relationship recursively when serialized."""
    return (
        db.query(Comment)
        .options(joinedload(Comment.author), joinedload(Comment.replies).joinedload(Comment.author))
        .filter(Comment.post_id == post_id, Comment.parent_id.is_(None), Comment.is_deleted == False)  # noqa: E712
        .order_by(Comment.created_at.asc())
        .all()
    )


def update_comment(db: Session, comment: Comment, content: str) -> Comment:
    comment.content = content
    db.commit()
    db.refresh(comment)
    return comment


def soft_delete_comment(db: Session, comment: Comment) -> None:
    comment.is_deleted = True
    comment.content = "[deleted]"
    db.commit()
