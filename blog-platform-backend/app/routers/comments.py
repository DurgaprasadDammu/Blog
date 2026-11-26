# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Request, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limiter import limiter
from app.crud import comment as comment_crud
from app.crud import post as post_crud
from app.database import get_db
from app.models.user import RoleEnum, User
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.config import settings

router = APIRouter(prefix="/api/posts/{post_id:int}/comments", tags=["Comments"])


@router.get("", response_model=list[CommentOut])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    post = post_crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return comment_crud.list_top_level_comments_for_post(db, post_id)


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.COMMENT_RATE_LIMIT)
def create_comment(
    request: Request,
    post_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a comment or, if parent_id is set, a nested reply.
    Rate-limited per client IP to prevent comment spam."""
    post = post_crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if comment_in.parent_id:
        parent = comment_crud.get_comment(db, comment_in.parent_id)
        if not parent or parent.post_id != post_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent comment")

    try:
        comment = comment_crud.create_comment(db, comment_in, post_id=post_id, author_id=current_user.id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create comment: {exc}")


    return comment


@router.patch("/{comment_id}", response_model=CommentOut)
def update_comment(
    post_id: int,
    comment_id: int,
    comment_in: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = comment_crud.get_comment(db, comment_id)
    if not comment or comment.post_id != post_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if current_user.role != RoleEnum.admin and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this comment")

    return comment_crud.update_comment(db, comment, comment_in.content)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = comment_crud.get_comment(db, comment_id)
    if not comment or comment.post_id != post_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if current_user.role != RoleEnum.admin and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment")

    comment_crud.soft_delete_comment(db, comment)

