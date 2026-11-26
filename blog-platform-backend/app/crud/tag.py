from typing import List

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.models.tag import Tag
from app.utils.slug import generate_unique_slug


def get_or_create_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    """Given a list of tag names, returns existing Tag objects or creates new ones.
    Used to build the Many-to-Many relationship when creating/updating a post."""
    tags = []
    for raw_name in tag_names:
        name = raw_name.strip().lower()
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            slug = generate_unique_slug(db, Tag, name)
            tag = Tag(name=name, slug=slug)
            db.add(tag)
            db.flush()  # get tag.id without committing yet
        tags.append(tag)
    return tags


def list_tags(db: Session):
    return db.query(Tag).order_by(Tag.name).all()
