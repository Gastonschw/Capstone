"""
File upload API routes.
"""

from fastapi import APIRouter, Depends, File, UploadFile, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_optional_user_id
from services.folder_service import save_and_extract_zip
from services.discovery_service import run_file_discovery

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload-folder")
async def upload_folder(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a ZIP file containing a repository. Optionally scoped to user via X-User-Id header."""
    owner_user_id = get_optional_user_id(request)
    repository = await save_and_extract_zip(file, db, name, owner_user_id=owner_user_id)

    # Run file discovery
    discovery_stats = await run_file_discovery(
        repository.local_path,
        db,
        repository.id
    )

    return {
        "id": repository.id,
        "name": repository.name,
        "source_type": repository.source_type,
        "message": "Repository uploaded successfully",
        "discovery_stats": discovery_stats
    }
