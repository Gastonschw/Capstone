import os
import json
import shutil
import secrets
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import httpx
from cryptography.fernet import Fernet

from database import get_db, init_db, engine
from models import Repository, DiscoveredFile, IntegrityAnalysis, GitHubToken, Base
from schemas import (
    RepositoryResponse, RepositoryListResponse, DiscoveredFileResponse,
    IntegrityAnalysisResponse, GitHubRepo, GitHubImportRequest, FileSelectionUpdate
)
from integrity_agent_service import discover_files, run_integrity_analysis

# Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

# Create uploads directory
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Integrity Analyzer API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:3000", FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Helper functions
def get_session_id(request: Request, response: Response) -> str:
    """Get or create a session ID from cookies."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = secrets.token_urlsafe(32)
        response.set_cookie("session_id", session_id, httponly=True, samesite="lax", max_age=86400 * 30)
    return session_id


async def get_github_token(session_id: str, db: AsyncSession) -> Optional[str]:
    """Retrieve and decrypt GitHub token for a session."""
    result = await db.execute(select(GitHubToken).where(GitHubToken.session_id == session_id))
    token_record = result.scalar_one_or_none()
    if token_record:
        try:
            return fernet.decrypt(token_record.encrypted_token.encode()).decode()
        except Exception:
            return None
    return None


# ==================== Repository Management ====================

@app.get("/api/repositories", response_model=List[RepositoryListResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    """List all repositories."""
    result = await db.execute(
        select(Repository).order_by(Repository.created_at.desc())
    )
    repositories = result.scalars().all()

    response = []
    for repo in repositories:
        # Get file and analysis counts
        file_count = await db.execute(
            select(func.count(DiscoveredFile.id)).where(DiscoveredFile.repository_id == repo.id)
        )
        analysis_count = await db.execute(
            select(func.count(IntegrityAnalysis.id)).where(IntegrityAnalysis.repository_id == repo.id)
        )

        response.append(RepositoryListResponse(
            id=repo.id,
            name=repo.name,
            source_type=repo.source_type,
            github_url=repo.github_url,
            created_at=repo.created_at,
            file_count=file_count.scalar() or 0,
            analysis_count=analysis_count.scalar() or 0
        ))

    return response


@app.get("/api/repository/{repo_id}", response_model=RepositoryResponse)
async def get_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Get repository details with discovered files."""
    result = await db.execute(
        select(Repository)
        .options(selectinload(Repository.discovered_files))
        .where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repo


@app.delete("/api/repository/{repo_id}")
async def delete_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a repository and its files."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Delete local files
    if repo.local_path and os.path.exists(repo.local_path):
        shutil.rmtree(repo.local_path, ignore_errors=True)

    await db.delete(repo)
    await db.commit()

    return {"message": "Repository deleted"}


@app.put("/api/repository/{repo_id}/files/selection")
async def update_file_selection(
    repo_id: int,
    update: FileSelectionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update file selection status."""
    result = await db.execute(
        select(DiscoveredFile)
        .where(DiscoveredFile.repository_id == repo_id)
        .where(DiscoveredFile.id.in_(update.file_ids))
    )
    files = result.scalars().all()

    for f in files:
        f.is_selected = update.is_selected

    await db.commit()

    return {"message": f"Updated {len(files)} files"}


# ==================== File Upload ====================

@app.post("/api/upload-folder")
async def upload_folder(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a ZIP file containing the codebase."""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")

    # Create unique directory for this upload
    upload_id = secrets.token_urlsafe(8)
    extract_path = UPLOAD_DIR / upload_id

    try:
        # Save and extract ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        extract_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        os.unlink(tmp_path)

        # Handle single root directory (common in ZIP files)
        items = list(extract_path.iterdir())
        if len(items) == 1 and items[0].is_dir():
            actual_path = items[0]
        else:
            actual_path = extract_path

        # Create repository record
        repo_name = file.filename.replace('.zip', '')
        repo = Repository(
            name=repo_name,
            source_type='folder_upload',
            local_path=str(actual_path)
        )
        db.add(repo)
        await db.commit()
        await db.refresh(repo)

        # Run discovery in background
        background_tasks.add_task(run_discovery_background, repo.id, str(actual_path))

        return {"repository_id": repo.id, "message": "Upload successful, discovery in progress"}

    except Exception as e:
        if extract_path.exists():
            shutil.rmtree(extract_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


async def run_discovery_background(repo_id: int, repo_path: str):
    """Run file discovery in background."""
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Clear existing discovered files
            await db.execute(
                select(DiscoveredFile).where(DiscoveredFile.repository_id == repo_id)
            )
            result = await db.execute(
                select(DiscoveredFile).where(DiscoveredFile.repository_id == repo_id)
            )
            for f in result.scalars().all():
                await db.delete(f)

            # Run discovery
            discovered = await discover_files(repo_path)

            # Save discovered files
            for f in discovered:
                file_record = DiscoveredFile(
                    repository_id=repo_id,
                    file_path=f.file_path,
                    file_type=f.file_type,
                    language=f.language,
                    relevance_score=f.relevance_score,
                    content_preview=f.content_preview,
                    is_selected=f.relevance_score >= 50  # Auto-select high relevance files
                )
                db.add(file_record)

            await db.commit()

        except Exception as e:
            print(f"Discovery error: {e}")


@app.post("/api/repository/{repo_id}/rediscover")
async def rediscover_files(
    repo_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Re-run file discovery for a repository."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    background_tasks.add_task(run_discovery_background, repo_id, repo.local_path)

    return {"message": "Re-discovery started"}


# ==================== GitHub Integration ====================

@app.get("/api/github/auth")
async def github_auth(request: Request, response: Response):
    """Initiate GitHub OAuth flow."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    session_id = get_session_id(request, response)
    state = secrets.token_urlsafe(16)

    # Store state in cookie for verification
    response = RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo&state={state}"
    )
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=600)
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax", max_age=86400 * 30)

    return response


@app.get("/api/github/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    stored_state = request.cookies.get("oauth_state")
    if state != stored_state:
        return RedirectResponse(url=f"{FRONTEND_URL}?github_error=invalid_state")

    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url=f"{FRONTEND_URL}?github_error=no_session")

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code
            },
            headers={"Accept": "application/json"}
        )

        if token_response.status_code != 200:
            return RedirectResponse(url=f"{FRONTEND_URL}?github_error=token_exchange_failed")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            return RedirectResponse(url=f"{FRONTEND_URL}?github_error=no_token")

        # Get user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        )
        user_data = user_response.json()
        username = user_data.get("login", "unknown")

    # Store encrypted token
    encrypted_token = fernet.encrypt(access_token.encode()).decode()

    # Check if token exists for this session
    result = await db.execute(select(GitHubToken).where(GitHubToken.session_id == session_id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.encrypted_token = encrypted_token
        existing.github_username = username
    else:
        token_record = GitHubToken(
            session_id=session_id,
            encrypted_token=encrypted_token,
            github_username=username
        )
        db.add(token_record)

    await db.commit()

    return RedirectResponse(url=f"{FRONTEND_URL}?github_success=true")


@app.get("/api/github/status")
async def github_status(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Check GitHub authentication status."""
    session_id = get_session_id(request, response)

    result = await db.execute(select(GitHubToken).where(GitHubToken.session_id == session_id))
    token_record = result.scalar_one_or_none()

    if token_record:
        return {
            "authenticated": True,
            "username": token_record.github_username
        }

    return {"authenticated": False}


@app.get("/api/github/repos", response_model=List[GitHubRepo])
async def list_github_repos(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """List user's GitHub repositories."""
    session_id = get_session_id(request, response)
    token = await get_github_token(session_id, db)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with GitHub")

    async with httpx.AsyncClient() as client:
        repos_response = await client.get(
            "https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={"Authorization": f"token {token}"}
        )

        if repos_response.status_code != 200:
            raise HTTPException(status_code=repos_response.status_code, detail="Failed to fetch repositories")

        repos = repos_response.json()

    return [
        GitHubRepo(
            id=r["id"],
            name=r["name"],
            full_name=r["full_name"],
            description=r.get("description"),
            private=r["private"],
            html_url=r["html_url"],
            default_branch=r.get("default_branch", "main")
        )
        for r in repos
    ]


@app.post("/api/github/import")
async def import_github_repo(
    import_request: GitHubImportRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Import a GitHub repository."""
    session_id = get_session_id(request, response)
    token = await get_github_token(session_id, db)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with GitHub")

    repo_full_name = import_request.repo_full_name

    # Download repository as ZIP
    async with httpx.AsyncClient() as client:
        # Get default branch
        repo_response = await client.get(
            f"https://api.github.com/repos/{repo_full_name}",
            headers={"Authorization": f"token {token}"}
        )

        if repo_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_data = repo_response.json()
        default_branch = repo_data.get("default_branch", "main")

        # Download ZIP
        zip_url = f"https://api.github.com/repos/{repo_full_name}/zipball/{default_branch}"
        zip_response = await client.get(
            zip_url,
            headers={"Authorization": f"token {token}"},
            follow_redirects=True
        )

        if zip_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to download repository")

    # Extract ZIP
    upload_id = secrets.token_urlsafe(8)
    extract_path = UPLOAD_DIR / upload_id

    try:
        extract_path.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            tmp.write(zip_response.content)
            tmp_path = tmp.name

        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        os.unlink(tmp_path)

        # Handle GitHub's nested directory structure
        items = list(extract_path.iterdir())
        if len(items) == 1 and items[0].is_dir():
            actual_path = items[0]
        else:
            actual_path = extract_path

        # Create repository record
        repo = Repository(
            name=repo_full_name.split('/')[-1],
            source_type='github',
            local_path=str(actual_path),
            github_url=repo_data["html_url"],
            github_repo_full_name=repo_full_name
        )
        db.add(repo)
        await db.commit()
        await db.refresh(repo)

        # Run discovery in background
        background_tasks.add_task(run_discovery_background, repo.id, str(actual_path))

        return {"repository_id": repo.id, "message": "Import successful, discovery in progress"}

    except Exception as e:
        if extract_path.exists():
            shutil.rmtree(extract_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/github/logout")
async def github_logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Logout from GitHub."""
    session_id = request.cookies.get("session_id")
    if session_id:
        result = await db.execute(select(GitHubToken).where(GitHubToken.session_id == session_id))
        token_record = result.scalar_one_or_none()
        if token_record:
            await db.delete(token_record)
            await db.commit()

    return {"message": "Logged out"}


# ==================== Integrity Analysis ====================

@app.post("/api/repository/{repo_id}/analyze")
async def start_analysis(
    repo_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start integrity analysis for a repository."""
    result = await db.execute(
        select(Repository)
        .options(selectinload(Repository.discovered_files))
        .where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get selected files
    selected_files = [f for f in repo.discovered_files if f.is_selected]

    if not selected_files:
        raise HTTPException(status_code=400, detail="No files selected for analysis")

    # Create analysis record
    analysis = IntegrityAnalysis(
        repository_id=repo_id,
        status="pending"
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Run analysis in background
    background_tasks.add_task(
        process_analysis_background,
        analysis.id,
        repo.local_path,
        [{"file_path": f.file_path, "file_type": f.file_type} for f in selected_files]
    )

    return {"analysis_id": analysis.id, "message": "Analysis started"}


async def process_analysis_background(analysis_id: int, repo_path: str, selected_files: List[dict]):
    """Process integrity analysis in background."""
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Update status to processing
            result = await db.execute(select(IntegrityAnalysis).where(IntegrityAnalysis.id == analysis_id))
            analysis = result.scalar_one_or_none()

            if not analysis:
                return

            analysis.status = "processing"
            await db.commit()

            # Run the analysis
            analysis_result = await run_integrity_analysis(repo_path, selected_files)

            # Store results
            analysis.confidentiality_report = json.dumps({
                'characteristic': analysis_result.confidentiality.characteristic,
                'score': analysis_result.confidentiality.score,
                'status': analysis_result.confidentiality.status,
                'description': analysis_result.confidentiality.description,
                'findings': analysis_result.confidentiality.findings,
                'recommendations': analysis_result.confidentiality.recommendations
            })

            analysis.data_integrity_report = json.dumps({
                'characteristic': analysis_result.data_integrity.characteristic,
                'score': analysis_result.data_integrity.score,
                'status': analysis_result.data_integrity.status,
                'description': analysis_result.data_integrity.description,
                'findings': analysis_result.data_integrity.findings,
                'recommendations': analysis_result.data_integrity.recommendations
            })

            analysis.authenticity_report = json.dumps({
                'characteristic': analysis_result.authenticity.characteristic,
                'score': analysis_result.authenticity.score,
                'status': analysis_result.authenticity.status,
                'description': analysis_result.authenticity.description,
                'findings': analysis_result.authenticity.findings,
                'recommendations': analysis_result.authenticity.recommendations
            })

            analysis.non_repudiation_report = json.dumps({
                'characteristic': analysis_result.non_repudiation.characteristic,
                'score': analysis_result.non_repudiation.score,
                'status': analysis_result.non_repudiation.status,
                'description': analysis_result.non_repudiation.description,
                'findings': analysis_result.non_repudiation.findings,
                'recommendations': analysis_result.non_repudiation.recommendations
            })

            analysis.accountability_report = json.dumps({
                'characteristic': analysis_result.accountability.characteristic,
                'score': analysis_result.accountability.score,
                'status': analysis_result.accountability.status,
                'description': analysis_result.accountability.description,
                'findings': analysis_result.accountability.findings,
                'recommendations': analysis_result.accountability.recommendations
            })

            analysis.resistance_report = json.dumps({
                'characteristic': analysis_result.resistance.characteristic,
                'score': analysis_result.resistance.score,
                'status': analysis_result.resistance.status,
                'description': analysis_result.resistance.description,
                'findings': analysis_result.resistance.findings,
                'recommendations': analysis_result.resistance.recommendations
            })

            analysis.overall_score = analysis_result.overall_score
            analysis.summary_report = json.dumps(analysis_result.summary)
            analysis.status = "completed"
            analysis.completed_at = datetime.utcnow()

            await db.commit()

        except Exception as e:
            print(f"Analysis error: {e}")
            result = await db.execute(select(IntegrityAnalysis).where(IntegrityAnalysis.id == analysis_id))
            analysis = result.scalar_one_or_none()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = str(e)
                await db.commit()


@app.get("/api/repository/{repo_id}/analyses")
async def list_analyses(repo_id: int, db: AsyncSession = Depends(get_db)):
    """List all analyses for a repository."""
    result = await db.execute(
        select(IntegrityAnalysis)
        .where(IntegrityAnalysis.repository_id == repo_id)
        .order_by(IntegrityAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()

    return [
        {
            "id": a.id,
            "status": a.status,
            "overall_score": a.overall_score,
            "created_at": a.created_at.isoformat(),
            "completed_at": a.completed_at.isoformat() if a.completed_at else None
        }
        for a in analyses
    ]


@app.get("/api/analysis/{analysis_id}")
async def get_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    """Get analysis details."""
    result = await db.execute(select(IntegrityAnalysis).where(IntegrityAnalysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    def parse_json_field(field):
        if field:
            try:
                return json.loads(field)
            except:
                return None
        return None

    return {
        "id": analysis.id,
        "repository_id": analysis.repository_id,
        "status": analysis.status,
        "error_message": analysis.error_message,
        "overall_score": analysis.overall_score,
        "confidentiality_report": parse_json_field(analysis.confidentiality_report),
        "data_integrity_report": parse_json_field(analysis.data_integrity_report),
        "authenticity_report": parse_json_field(analysis.authenticity_report),
        "non_repudiation_report": parse_json_field(analysis.non_repudiation_report),
        "accountability_report": parse_json_field(analysis.accountability_report),
        "resistance_report": parse_json_field(analysis.resistance_report),
        "summary_report": parse_json_field(analysis.summary_report),
        "created_at": analysis.created_at.isoformat(),
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
    }


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
