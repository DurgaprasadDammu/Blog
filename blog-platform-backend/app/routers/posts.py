import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_optional_user, require_roles
from app.crud import post as post_crud
from app.database import get_db
from app.models.post import StatusEnum
from app.models.user import RoleEnum, User
from app.schemas.post import PaginatedResponse, PostCreate, PostListItem, PostOut, PostStatusUpdate, PostUpdate

router = APIRouter(prefix="/api/posts", tags=["Posts"])


def _check_can_modify(post, current_user: User):
    """Authors can only modify their own posts; admins can modify any post."""
    if current_user.role != RoleEnum.admin and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this post",
        )


@router.get("", response_model=PaginatedResponse[PostListItem])
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by title, content, or tag name"),
    category_id: Optional[int] = None,
    tag: Optional[str] = None,
    status_filter: Optional[StatusEnum] = Query(None, alias="status"),
    author_id: Optional[int] = None,
    include_archived: bool = True,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Public listing of posts with pagination, search, and filters.
    Anonymous/regular users only ever see published posts. Authors/admins can
    pass status=draft (etc.) to see their own unpublished work."""
    effective_status = status_filter
    effective_author = author_id

    if current_user is None or current_user.role == RoleEnum.user:
        # Public / plain users only ever see published, non-deleted content
        effective_status = StatusEnum.published
    elif status_filter is not None and current_user.role == RoleEnum.author:
        # Authors requesting non-published statuses may only see their own posts
        if status_filter != StatusEnum.published:
            effective_author = current_user.id

    items, total = post_crud.list_posts(
        db,
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        tag=tag,
        status=effective_status,
        author_id=effective_author,
        include_archived=include_archived,
    )
    total_pages = math.ceil(total / page_size) if total else 0
    return PaginatedResponse(total=total, page=page, page_size=page_size, total_pages=total_pages, items=items)


@router.get("/{slug_or_id}", response_model=PostOut)
def get_post(
    slug_or_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    post = None
    if slug_or_id.isdigit():
        post = post_crud.get_post_by_id(db, int(slug_or_id))
    if not post:
        post = post_crud.get_post_by_slug(db, slug_or_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    is_owner_or_admin = current_user and (current_user.id == post.author_id or current_user.role == RoleEnum.admin)
    if post.status != StatusEnum.published and not is_owner_or_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Track view count only for published posts viewed by someone other than the author
    if post.status == StatusEnum.published and not (current_user and current_user.id == post.author_id):
        post = post_crud.increment_view_count(db, post)

    return post


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.author, RoleEnum.admin)),
):
    """Only authors and admins can create posts."""
    try:
        return post_crud.create_post(db, post_in, author_id=current_user.id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create post: {exc}")


@router.put("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    post_in: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.author, RoleEnum.admin)),
):
    post = post_crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _check_can_modify(post, current_user)

    try:
        return post_crud.update_post(db, post, post_in)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update post: {exc}")


@router.patch("/{post_id}/status", response_model=PostOut)
def update_post_status(
    post_id: int,
    status_in: PostStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.author, RoleEnum.admin)),
):
    """Publish, unpublish (draft), or archive a post."""
    post = post_crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _check_can_modify(post, current_user)
    return post_crud.set_post_status(db, post, status_in.status)


@router.post("/{post_id}/archive", response_model=PostOut)
def archive_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.author, RoleEnum.admin)),
):
    post = post_crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _check_can_modify(post, current_user)
    return post_crud.archive_post(db, post)


@router.post("/{post_id}/unarchive", response_model=PostOut)
def unarchive_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.author, RoleEnum.admin)),
):
    post = post_crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _check_can_modify(post, current_user)
    return post_crud.unarchive_post(db, post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.author, RoleEnum.admin)),
):
    """Soft delete — the post is hidden from all listings but preserved in the DB."""
    post = post_crud.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _check_can_modify(post, current_user)
    post_crud.soft_delete_post(db, post)
