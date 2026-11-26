# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.firebase.storage import upload_file, FirebaseNotConfiguredError

router = APIRouter(prefix="/api/media", tags=["Media"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_media_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload post cover images or other media files to Firebase Cloud Storage.
    Requires authentication."""
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # Upload to Firebase
        public_url = upload_file(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type
        )
        
        return {"url": public_url, "filename": file.filename}
        
    except FirebaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {exc}"
        )
