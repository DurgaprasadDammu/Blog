from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import tag as tag_crud
from app.database import get_db
from app.schemas.tag import TagOut

router = APIRouter(prefix="/api/tags", tags=["Tags"])


@router.get("", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    """List all tags (tags are otherwise created implicitly via posts)."""
    return tag_crud.list_tags(db)
