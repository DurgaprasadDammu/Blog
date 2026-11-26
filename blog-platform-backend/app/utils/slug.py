import uuid

from slugify import slugify
from sqlalchemy.orm import Session


def generate_unique_slug(db: Session, model, text: str, slug_field: str = "slug") -> str:
    """Generate a URL-friendly slug from `text`, appending a short random suffix
    if the base slug already exists for the given model."""
    base_slug = slugify(text)[:250] or "item"
    slug = base_slug
    query_field = getattr(model, slug_field)

    while db.query(model).filter(query_field == slug).first() is not None:
        suffix = uuid.uuid4().hex[:6]
        slug = f"{base_slug}-{suffix}"

    return slug
