"""
Folder Upload Service

Handles ZIP file uploads and extraction for repository analysis.
"""

import os
import uuid
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from models import Repository, RepositorySource


# Repository storage path
REPOS_DIR = Path("uploads/repos")
REPOS_DIR.mkdir(parents=True, exist_ok=True)

# Maximum upload size (100MB)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024

# Allowed archive types
ALLOWED_ARCHIVE_TYPES = [
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
]


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
    db: Session,
    repo_name: Optional[str] = None
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
    
    # Determine repository name
    if not repo_name:
        repo_name = Path(file.filename).stem if file.filename else "Uploaded Repository"
    
    # Create unique directory for this repo
    repo_uuid = str(uuid.uuid4())
    repo_path = REPOS_DIR / repo_uuid
    repo_path.mkdir(parents=True, exist_ok=True)
    
    # Save the ZIP file temporarily
    zip_path = repo_path / "archive.zip"
    
    try:
        # Read and save the file with size limit check
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            shutil.rmtree(repo_path)
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)}MB"
            )
        
        with open(zip_path, "wb") as f:
            f.write(content)
        
        # Extract the ZIP file
        extract_zip_safely(zip_path, repo_path)
        
        # Remove the ZIP file after extraction
        zip_path.unlink()
        
        # If extraction created a single root folder, move contents up
        flatten_single_root_directory(repo_path)
        
        # Create Repository record
        repository = Repository(
            name=repo_name,
            source_type=RepositorySource.folder_upload.value,
            local_path=str(repo_path),
        )
        db.add(repository)
        db.commit()
        db.refresh(repository)
        
        return repository
        
    except zipfile.BadZipFile:
        shutil.rmtree(repo_path, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid ZIP file. The file appears to be corrupted."
        )
    except Exception as e:
        shutil.rmtree(repo_path, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process ZIP file: {str(e)}"
        )


def extract_zip_safely(zip_path: Path, extract_to: Path) -> None:
    """
    Safely extract a ZIP file, preventing path traversal attacks.
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.namelist():
            # Skip directories
            if member.endswith('/'):
                continue
            
            # Prevent path traversal attacks
            member_path = Path(member)
            if member_path.is_absolute() or '..' in member_path.parts:
                raise HTTPException(
                    status_code=400,
                    detail="ZIP file contains invalid paths"
                )
            
            # Skip hidden files and common ignore patterns
            if should_skip_file(member):
                continue
            
            # Extract the file
            target_path = extract_to / member
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                target.write(source.read())


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
    items = [item for item in repo_path.iterdir() if item.name != 'archive.zip']
    
    if len(items) == 1 and items[0].is_dir():
        root_dir = items[0]
        
        # Move all contents from the single directory to repo_path
        for item in root_dir.iterdir():
            dest = repo_path / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(item), str(dest))
        
        # Remove the now-empty root directory
        root_dir.rmdir()


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
