"""
Folder Upload Service

Handles ZIP file uploads and extraction for repository analysis.
"""

import uuid
import shutil
import zipfile
import stat
import tempfile
import asyncio
from pathlib import Path, PureWindowsPath
from typing import Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import REPOS_DIR, MAX_UPLOAD_SIZE, ALLOWED_ARCHIVE_TYPES
from models.repository import Repository, RepositorySource
from services.user_service import require_registered_user

MAX_EXPANDED_SIZE = 512 * 1024 * 1024
MAX_FILE_SIZE = 32 * 1024 * 1024
MAX_ARCHIVE_FILES = 10000
CHUNK_SIZE = 1024 * 1024


async def run_file_operation(operation, *args):
    """Wait for filesystem workers before cleaning their directories on cancellation."""
    task = asyncio.create_task(asyncio.to_thread(operation, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        except Exception:
            pass  # Preserve cancellation; the caller removes partial output.
        raise


def validate_zip_file(file: UploadFile) -> None:
    """Validate that the uploaded file is a valid ZIP archive."""
    if file.content_type not in ALLOWED_ARCHIVE_TYPES:
        # Also check file extension as backup
        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Please upload a ZIP file. Got: {file.content_type}"
            )


async def save_and_extract_zip(
    file: UploadFile,
    db: AsyncSession,
    repo_name: str = None,
    *,
    owner_user_id: Optional[str] = None,
) -> Repository:
    """
    Save uploaded ZIP file and extract its contents.

    Args:
        file: The uploaded ZIP file
        db: Database session
        repo_name: Optional name for the repository (defaults to filename without extension)

    Returns:
        Repository record with extracted files
    """
    validate_zip_file(file)

    link_uid = await require_registered_user(db, owner_user_id)

    # Determine repository name
    if not repo_name:
        repo_name = Path(file.filename).stem if file.filename else "Uploaded Repository"

    # Create unique directory for this repo
    repo_uuid = str(uuid.uuid4())
    repo_path = REPOS_DIR / repo_uuid
    repo_path.mkdir(parents=True, exist_ok=True)

    try:
        # Keep the compressed archive outside the extraction destination.
        with tempfile.TemporaryDirectory(prefix="repository-upload-") as temporary:
            zip_path = Path(temporary) / "archive.zip"
            size = 0
            with zip_path.open("wb") as target:
                while chunk := await file.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > MAX_UPLOAD_SIZE:
                        raise HTTPException(400, "Compressed archive exceeds upload limit")
                    target.write(chunk)
            await run_file_operation(extract_zip_safely, zip_path, repo_path)
        await run_file_operation(flatten_single_root_directory, repo_path)

        repository = Repository(
            name=repo_name,
            source_type=RepositorySource.folder_upload.value,
            local_path=str(repo_path),
            owner_user_id=link_uid,
        )
        db.add(repository)
        await db.flush()

        return repository

    except zipfile.BadZipFile:
        shutil.rmtree(repo_path, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid ZIP file. The file appears to be corrupted."
        )
    except HTTPException:
        shutil.rmtree(repo_path, ignore_errors=True)
        raise
    except asyncio.CancelledError:
        shutil.rmtree(repo_path, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(repo_path, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process ZIP file: {str(e)}"
        )


def extract_zip_safely(zip_path: Path, extract_to: Path) -> None:
    """Extract bounded regular files only, with portable path containment."""
    if zip_path.stat().st_size > MAX_UPLOAD_SIZE:
        raise HTTPException(400, "Compressed archive exceeds upload limit")
    base = extract_to.resolve()
    expanded = 0
    with zipfile.ZipFile(zip_path, "r") as archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_FILES:
            raise HTTPException(400, "Archive contains too many entries")
        declared_size = 0
        for member in members:
            name = member.filename.replace("\\", "/")
            parts = name.split("/")
            mode = member.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if (
                not name or name.startswith("/") or PureWindowsPath(name).drive
                or ".." in parts or any(
                    ":" in part or part.rstrip(" .") != part
                    or part.split(".")[0].upper() in {
                        "CON", "PRN", "AUX", "NUL",
                        *(f"COM{i}" for i in range(1, 10)),
                        *(f"LPT{i}" for i in range(1, 10)),
                    }
                    for part in parts if part
                )
                or kind not in (0, stat.S_IFREG, stat.S_IFDIR)
            ):
                raise HTTPException(400, "ZIP file contains invalid paths or links")
            target = base.joinpath(*parts)
            if not target.resolve().is_relative_to(base):
                raise HTTPException(400, "ZIP file escapes repository directory")
            if target.is_symlink() or any(p.is_symlink() for p in target.parents):
                raise HTTPException(400, "ZIP file contains a symbolic link")
            declared_size += member.file_size
            if member.file_size > MAX_FILE_SIZE or declared_size > MAX_EXPANDED_SIZE:
                raise HTTPException(400, "Expanded archive exceeds size limit")
            if member.is_dir() or name.endswith("/") or should_skip_file(name):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with archive.open(member) as source, target.open("xb") as destination:
                while chunk := source.read(CHUNK_SIZE):
                    written += len(chunk)
                    expanded += len(chunk)
                    if written > MAX_FILE_SIZE or expanded > MAX_EXPANDED_SIZE:
                        raise HTTPException(400, "Expanded archive exceeds size limit")
                    destination.write(chunk)


def should_skip_file(file_path: str) -> bool:
    """
    Determine if a file should be skipped during extraction.
    Skips system files, hidden files, and common non-essential directories.
    """
    skip_patterns = [
        '__MACOSX',
        '.DS_Store',
        'Thumbs.db',
        '.git/',
        'node_modules/',
        '__pycache__/',
        '.venv/',
        'venv/',
        '.env',
        '.idea/',
        '.vscode/',
    ]

    path_lower = file_path.lower()
    for pattern in skip_patterns:
        if pattern.lower() in path_lower:
            return True

    # Skip hidden files (starting with .)
    parts = Path(file_path).parts
    for part in parts:
        if part.startswith('.') and part not in ['.gitkeep', '.gitignore']:
            return True

    return False


def flatten_single_root_directory(repo_path: Path) -> None:
    """
    If extraction created a single root folder, move its contents up one level.
    This handles ZIPs that have a single root directory containing all files.
    """
    items = list(repo_path.iterdir())
    if len(items) == 1 and items[0].is_dir():
        # Rename the root outside the destination before moving its children.
        # In particular project/project must not delete its own source ancestor.
        with tempfile.TemporaryDirectory(dir=repo_path.parent, prefix="flatten-") as temporary:
            staged = Path(temporary) / "root"
            shutil.move(str(items[0]), str(staged))
            for item in staged.iterdir():
                shutil.move(str(item), str(repo_path / item.name))


def delete_repository_files(local_path: str) -> bool:
    """Delete the local files for a repository."""
    try:
        path = Path(local_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
        return False
    except Exception:
        return False


def get_repository_file_count(local_path: str) -> int:
    """Count the number of files in a repository."""
    path = Path(local_path)
    if not path.exists():
        return 0

    count = 0
    for _ in path.rglob('*'):
        if _.is_file():
            count += 1
    return count
