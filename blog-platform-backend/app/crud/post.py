from datetime import datetime
from typing import Optional

# pyrefly: ignore [missing-import]
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.crud.tag import get_or_create_tags
from app.models.post import Post, StatusEnum
from app.models.tag import Tag
from app.schemas.post import PostCreate, PostUpdate
from app.utils.slug import generate_unique_slug


def _base_query(db: Session):
    return db.query(Post).options(
        joinedload(Post.author), joinedload(Post.category), joinedload(Post.tags)
    )


def get_post_by_id(db: Session, post_id: int, include_deleted: bool = False) -> Optional[Post]:
    query = _base_query(db).filter(Post.id == post_id)
    if not include_deleted:
        query = query.filter(Post.is_deleted == False)  # noqa: E712
    return query.first()


def get_post_by_slug(db: Session, slug: str, include_deleted: bool = False) -> Optional[Post]:
    query = _base_query(db).filter(Post.slug == slug)
    if not include_deleted:
        query = query.filter(Post.is_deleted == False)  # noqa: E712
    return query.first()


def create_post(db: Session, post_in: PostCreate, author_id: int) -> Post:
    slug = generate_unique_slug(db, Post, post_in.title)
    tags = get_or_create_tags(db, post_in.tag_names)

    db_post = Post(
        title=post_in.title,
        slug=slug,
        content=post_in.content,
        excerpt=post_in.excerpt,
        category_id=post_in.category_id,
        status=post_in.status,
        author_id=author_id,
        tags=tags,
        published_at=datetime.utcnow() if post_in.status == StatusEnum.published else None,
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def update_post(db: Session, post: Post, post_in: PostUpdate) -> Post:
    data = post_in.model_dump(exclude_unset=True, exclude={"tag_names"})

    if "title" in data and data["title"] != post.title:
        post.slug = generate_unique_slug(db, Post, data["title"])

    for field, value in data.items():
        setattr(post, field, value)

    if post_in.tag_names is not None:
        post.tags = get_or_create_tags(db, post_in.tag_names)

    # If status transitions to published for the first time, stamp published_at
    if post_in.status == StatusEnum.published and post.published_at is None:
        post.published_at = datetime.utcnow()

    db.commit()
    db.refresh(post)
    return post


def set_post_status(db: Session, post: Post, status: StatusEnum) -> Post:
    post.status = status
    if status == StatusEnum.published and post.published_at is None:
        post.published_at = datetime.utcnow()
    if status == StatusEnum.archived:
        post.is_archived = True
    db.commit()
    db.refresh(post)
    return post


def archive_post(db: Session, post: Post) -> Post:
    post.is_archived = True
    post.status = StatusEnum.archived
    db.commit()
    db.refresh(post)
    return post


def unarchive_post(db: Session, post: Post) -> Post:
    post.is_archived = False
    post.status = StatusEnum.draft
    db.commit()
    db.refresh(post)
    return post


def soft_delete_post(db: Session, post: Post) -> None:
    post.is_deleted = True
    db.commit()


def increment_view_count(db: Session, post: Post) -> Post:
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return post


def list_posts(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    tag: Optional[str] = None,
    status: Optional[StatusEnum] = None,
    author_id: Optional[int] = None,
    include_deleted: bool = False,
    include_archived: bool = True,
):
    query = _base_query(db)

    if not include_deleted:
        query = query.filter(Post.is_deleted == False)  # noqa: E712
    if not include_archived:
        query = query.filter(Post.is_archived == False)  # noqa: E712
    if status is not None:
        query = query.filter(Post.status == status)
    if category_id is not None:
        query = query.filter(Post.category_id == category_id)
    if author_id is not None:
        query = query.filter(Post.author_id == author_id)
    tags_joined = False
    if tag is not None:
        query = query.join(Post.tags).filter(Tag.name == tag.lower())
        tags_joined = True
    if search:
        like_term = f"%{search}%"
        if not tags_joined:
            query = query.outerjoin(Post.tags)
        # Search across title, content, and tag names as required
        query = query.filter(
            or_(
                Post.title.ilike(like_term),
                Post.content.ilike(like_term),
                Tag.name.ilike(like_term),
            )
        )

    total = query.distinct().count()
    items = (
        query.distinct()
        .order_by(Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total
