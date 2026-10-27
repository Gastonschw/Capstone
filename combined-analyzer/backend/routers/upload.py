"""
File upload API routes.
"""

import shutil
from typing import Optional
from fastapi import APIRouter, Depends, File, Header, UploadFile, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user_id
from services.folder_service import save_and_extract_zip
from services.discovery_service import run_file_discovery

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload-folder")
async def upload_folder(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(None),
    db: AsyncSession = Depends(get_db),
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
    owner_user_id: str = Depends(get_current_user_id),
):
    """Upload a repository for the verified, registered owner."""
    repository = None
    try:
        repository = await save_and_extract_zip(file, db, name, owner_user_id=owner_user_id)
        discovery_stats = await run_file_discovery(
            repository.local_path, db, repository.id, api_key=tamu_api_key,
        )
        await db.commit()
    except BaseException:
        await db.rollback()
        if repository is not None:
            shutil.rmtree(repository.local_path, ignore_errors=True)
        raise

    return {
        "id": repository.id,
        "name": repository.name,
        "source_type": repository.source_type,
        "message": "Repository uploaded successfully",
        "discovery_stats": discovery_stats
    }
