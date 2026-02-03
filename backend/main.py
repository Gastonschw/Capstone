import json
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import engine, get_db, Base
from models import Analysis, AnalysisStatus
from schemas import AnalysisResponse, AnalysisListItem
import claude_service

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

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


async def process_analysis(analysis_id: int, image_path: str, user_stories: str):
    """Background task to run the Claude analysis."""
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
    """Upload ERD image and user stories for analysis."""
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
            status=a.status
        )
        for a in analyses
    ]


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
