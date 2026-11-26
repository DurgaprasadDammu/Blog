from typing import Optional

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.slug import generate_unique_slug


def get_category(db: Session, category_id: int) -> Optional[Category]:
    return db.query(Category).filter(Category.id == category_id).first()


def get_category_by_name(db: Session, name: str) -> Optional[Category]:
    return db.query(Category).filter(Category.name == name).first()


def list_categories(db: Session):
    return db.query(Category).order_by(Category.name).all()


def create_category(db: Session, category_in: CategoryCreate) -> Category:
    slug = generate_unique_slug(db, Category, category_in.name)
    db_category = Category(name=category_in.name, slug=slug, description=category_in.description)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def update_category(db: Session, category: Category, category_in: CategoryUpdate) -> Category:
    if category_in.name is not None and category_in.name != category.name:
        category.name = category_in.name
        category.slug = generate_unique_slug(db, Category, category_in.name)
    if category_in.description is not None:
        category.description = category_in.description
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
