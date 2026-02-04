import json
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, Depends, HTTPException, BackgroundTasks, Cookie, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import engine, get_db, Base
from models import Analysis, AnalysisStatus, Repository, DiscoveredFile, FileType
from schemas import (
    AnalysisResponse, AnalysisListItem, 
    RepositoryResponse, RepositoryDetailResponse, RepositoryListItem,
    DiscoveredFileResponse, FileSelectionUpdate,
    GitHubRepoInfo, GitHubImportRequest, GitHubAuthStatus,
    StartAnalysisRequest
)
import claude_service
import github_service
import folder_service
import agent_service

load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ERD Analysis API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
REPOS_DIR = Path("uploads/repos")
REPOS_DIR.mkdir(parents=True, exist_ok=True)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ============== Helper Functions ==============

def get_session_id(session_id: Optional[str] = Cookie(None)) -> str:
    """Get or create a session ID from cookie."""
    if session_id:
        return session_id
    return str(uuid.uuid4())


# ============== Legacy Single-File Analysis ==============

async def process_analysis(analysis_id: int, image_path: str, user_stories: str):
    """Background task to run the Claude analysis (legacy single-file mode)."""
    from database import SessionLocal
    db = SessionLocal()

    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return

        analysis.status = AnalysisStatus.processing.value
        db.commit()

        # Run the two-step analysis
        extracted_erd, report = await claude_service.run_full_analysis(image_path, user_stories)

        analysis.extracted_erd = json.dumps(extracted_erd)
        analysis.report = json.dumps(report)
        analysis.status = AnalysisStatus.completed.value
        db.commit()

    except Exception as e:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = AnalysisStatus.failed.value
            analysis.error_message = str(e)
            db.commit()
    finally:
        db.close()


@app.post("/api/analyze", response_model=AnalysisResponse)
async def create_analysis(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    user_stories: str = Form(...),
    db: Session = Depends(get_db)
):
    """Upload ERD image and user stories for analysis (legacy single-file mode)."""
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Save uploaded file
    file_extension = Path(image.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    with open(file_path, "wb") as f:
        content = await image.read()
        f.write(content)

    # Create analysis record
    analysis = Analysis(
        image_filename=unique_filename,
        user_stories=user_stories,
        status=AnalysisStatus.pending.value
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Start background processing
    background_tasks.add_task(
        process_analysis,
        analysis.id,
        str(file_path),
        user_stories
    )

    return AnalysisResponse(
        id=analysis.id,
        created_at=analysis.created_at,
        image_filename=analysis.image_filename,
        user_stories=analysis.user_stories,
        status=analysis.status
    )


# ============== GitHub OAuth Endpoints ==============

@app.get("/api/github/auth")
async def github_auth(
    session_id: str = Depends(get_session_id)
):
    """Initiate GitHub OAuth flow."""
    if not github_service.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET."
        )
    
    auth_url = github_service.get_github_auth_url(state=session_id)
    response = RedirectResponse(url=auth_url)
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="lax")
    return response


@app.get("/api/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    try:
        # Exchange code for token
        token_data = await github_service.exchange_code_for_token(code)
        
        if "error" in token_data:
            raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth failed"))
        
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        # Get user info
        user_info = await github_service.get_github_user(access_token)
        
        # Save token
        github_service.save_github_token(db, state, access_token, user_info)
        
        # Redirect to frontend
        response = RedirectResponse(url="http://localhost:5173?github_auth=success")
        response.set_cookie(key="session_id", value=state, httponly=True, samesite="lax")
        return response
        
    except Exception as e:
        return RedirectResponse(url=f"http://localhost:5173?github_auth=error&message={str(e)}")


@app.get("/api/github/status", response_model=GitHubAuthStatus)
async def github_auth_status(
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Check if user is authenticated with GitHub."""
    if not session_id:
        return GitHubAuthStatus(authenticated=False)
    
    status = github_service.get_github_auth_status(db, session_id)
    return GitHubAuthStatus(**status)


@app.get("/api/github/repos", response_model=List[GitHubRepoInfo])
async def list_github_repos(
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """List GitHub repositories for authenticated user."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated with GitHub")
    
    access_token = github_service.get_github_token(db, session_id)
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated with GitHub")
    
    try:
        repos = github_service.list_github_repos(access_token)
        return [GitHubRepoInfo(**repo) for repo in repos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")


@app.post("/api/github/import", response_model=RepositoryResponse)
async def import_github_repo(
    request: GitHubImportRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Import a GitHub repository for analysis."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated with GitHub")
    
    access_token = github_service.get_github_token(db, session_id)
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated with GitHub")
    
    try:
        repository = github_service.clone_github_repo(access_token, request.repo_full_name, db)
        
        # Run file discovery in background
        background_tasks.add_task(
            run_discovery_background,
            repository.id
        )
        
        return RepositoryResponse(
            id=repository.id,
            created_at=repository.created_at,
            name=repository.name,
            source_type=repository.source_type,
            github_url=repository.github_url,
            github_repo_full_name=repository.github_repo_full_name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import repository: {str(e)}")


@app.post("/api/github/logout")
async def github_logout(
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Logout from GitHub (delete stored token)."""
    if session_id:
        github_service.delete_github_token(db, session_id)
    return {"status": "logged out"}


# ============== Folder Upload Endpoints ==============

@app.post("/api/upload-folder", response_model=RepositoryResponse)
async def upload_folder(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a ZIP file containing a project folder for analysis."""
    repository = await folder_service.save_and_extract_zip(file, db, name)
    
    # Run file discovery in background
    background_tasks.add_task(
        run_discovery_background,
        repository.id
    )
    
    return RepositoryResponse(
        id=repository.id,
        created_at=repository.created_at,
        name=repository.name,
        source_type=repository.source_type
    )


# ============== Repository Management Endpoints ==============

@app.get("/api/repositories", response_model=List[RepositoryListItem])
async def list_repositories(db: Session = Depends(get_db)):
    """List all repositories."""
    repos = db.query(Repository).order_by(Repository.created_at.desc()).all()
    return [
        RepositoryListItem(
            id=r.id,
            created_at=r.created_at,
            name=r.name,
            source_type=r.source_type
        )
        for r in repos
    ]


@app.get("/api/repository/{repository_id}", response_model=RepositoryDetailResponse)
async def get_repository(repository_id: int, db: Session = Depends(get_db)):
    """Get repository details including discovered files."""
    repository = db.query(Repository).filter(Repository.id == repository_id).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    files = db.query(DiscoveredFile).filter(
        DiscoveredFile.repository_id == repository_id
    ).order_by(DiscoveredFile.confidence_score.desc()).all()
    
    return RepositoryDetailResponse(
        id=repository.id,
        created_at=repository.created_at,
        name=repository.name,
        source_type=repository.source_type,
        github_url=repository.github_url,
        github_repo_full_name=repository.github_repo_full_name,
        discovered_files=[
            DiscoveredFileResponse(
                id=f.id,
                file_path=f.file_path,
                file_type=f.file_type,
                confidence_score=f.confidence_score,
                content_preview=f.content_preview,
                is_selected=f.is_selected
            )
            for f in files
        ]
    )


@app.get("/api/repository/{repository_id}/files", response_model=List[DiscoveredFileResponse])
async def get_repository_files(repository_id: int, db: Session = Depends(get_db)):
    """Get discovered files for a repository."""
    repository = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    files = db.query(DiscoveredFile).filter(
        DiscoveredFile.repository_id == repository_id
    ).order_by(DiscoveredFile.confidence_score.desc()).all()
    
    return [
        DiscoveredFileResponse(
            id=f.id,
            file_path=f.file_path,
            file_type=f.file_type,
            confidence_score=f.confidence_score,
            content_preview=f.content_preview,
            is_selected=f.is_selected
        )
        for f in files
    ]


@app.put("/api/repository/{repository_id}/files/selection")
async def update_file_selection(
    repository_id: int,
    selection: FileSelectionUpdate,
    db: Session = Depends(get_db)
):
    """Update which files are selected for analysis."""
    repository = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    db.query(DiscoveredFile).filter(
        DiscoveredFile.id.in_(selection.file_ids),
        DiscoveredFile.repository_id == repository_id
    ).update({DiscoveredFile.is_selected: selection.is_selected}, synchronize_session=False)
    
    db.commit()
    
    return {"status": "updated", "updated_count": len(selection.file_ids)}


@app.post("/api/repository/{repository_id}/rediscover")
async def rediscover_files(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Re-run file discovery for a repository."""
    repository = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Run discovery in background
    background_tasks.add_task(
        run_discovery_background,
        repository.id
    )
    
    return {"status": "discovery_started"}


@app.delete("/api/repository/{repository_id}")
async def delete_repository(repository_id: int, db: Session = Depends(get_db)):
    """Delete a repository and its files."""
    repository = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Delete local files
    folder_service.delete_repository_files(repository.local_path)
    
    # Delete database records (cascades to discovered files and analyses)
    db.delete(repository)
    db.commit()
    
    return {"status": "deleted"}


# ============== Repository Analysis Endpoints ==============

async def run_discovery_background(repository_id: int):
    """Background task to run file discovery."""
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if repository:
            await agent_service.run_discovery_only(repository, db)
    except Exception as e:
        print(f"Discovery failed for repository {repository_id}: {e}")
    finally:
        db.close()


async def process_repository_analysis(analysis_id: int, repository_id: int):
    """Background task to run the full agentic analysis workflow."""
    from database import SessionLocal
    db = SessionLocal()

    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        
        if not analysis or not repository:
            return

        analysis.status = AnalysisStatus.processing.value
        db.commit()

        # Run the agentic workflow
        result = await agent_service.run_repository_analysis(repository, db)

        if result.success:
            analysis.uml_structure = json.dumps(result.uml_structure)
            analysis.report = json.dumps(result.report)
            analysis.status = AnalysisStatus.completed.value
        else:
            analysis.status = AnalysisStatus.failed.value
            analysis.error_message = result.error

        db.commit()

    except Exception as e:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = AnalysisStatus.failed.value
            analysis.error_message = str(e)
            db.commit()
    finally:
        db.close()


@app.post("/api/repository/{repository_id}/analyze", response_model=AnalysisResponse)
async def start_repository_analysis(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start analysis on a repository using the agentic workflow."""
    repository = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Check if files have been discovered
    file_count = db.query(DiscoveredFile).filter(
        DiscoveredFile.repository_id == repository_id
    ).count()
    
    if file_count == 0:
        raise HTTPException(
            status_code=400, 
            detail="No files discovered yet. Please wait for file discovery to complete or trigger rediscovery."
        )
    
    # Create analysis record
    analysis = Analysis(
        repository_id=repository_id,
        status=AnalysisStatus.pending.value
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    # Start background processing
    background_tasks.add_task(
        process_repository_analysis,
        analysis.id,
        repository_id
    )
    
    return AnalysisResponse(
        id=analysis.id,
        created_at=analysis.created_at,
        repository_id=analysis.repository_id,
        status=analysis.status
    )


# ============== Analysis Retrieval Endpoints ==============

@app.get("/api/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get analysis status and results."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisResponse(
        id=analysis.id,
        created_at=analysis.created_at,
        image_filename=analysis.image_filename,
        user_stories=analysis.user_stories,
        repository_id=analysis.repository_id,
        uml_structure=json.loads(analysis.uml_structure) if analysis.uml_structure else None,
        extracted_erd=json.loads(analysis.extracted_erd) if analysis.extracted_erd else None,
        report=json.loads(analysis.report) if analysis.report else None,
        status=analysis.status,
        error_message=analysis.error_message
    )


@app.get("/api/analyses", response_model=List[AnalysisListItem])
async def list_analyses(db: Session = Depends(get_db)):
    """List all analyses (history)."""
    analyses = db.query(Analysis).order_by(Analysis.created_at.desc()).all()

    return [
        AnalysisListItem(
            id=a.id,
            created_at=a.created_at,
            status=a.status,
            repository_id=a.repository_id
        )
        for a in analyses
    ]


@app.get("/api/repository/{repository_id}/analyses", response_model=List[AnalysisListItem])
async def list_repository_analyses(repository_id: int, db: Session = Depends(get_db)):
    """List all analyses for a specific repository."""
    repository = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    analyses = db.query(Analysis).filter(
        Analysis.repository_id == repository_id
    ).order_by(Analysis.created_at.desc()).all()

    return [
        AnalysisListItem(
            id=a.id,
            created_at=a.created_at,
            status=a.status,
            repository_id=a.repository_id
        )
        for a in analyses
    ]


# ============== Utility Endpoints ==============

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
