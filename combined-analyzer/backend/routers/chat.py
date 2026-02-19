"""
Chat API routes for discussing analysis results.

Uses Server-Sent Events (SSE) for streaming responses.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.chat_service import (
    stream_erd_chat,
    stream_integrity_chat,
    fetch_tamu_models,
    TAMU_DEFAULT_MODEL,
)


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    history: List[ChatMessage] = []


async def event_generator(
    stream_func,
    analysis_id: int,
    message: str,
    history: list,
    db: AsyncSession,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """
    Generate Server-Sent Events from a streaming function.
    """
    try:
        async for chunk in stream_func(
            analysis_id,
            message,
            history,
            db,
            model=model,
            api_key=api_key,
        ):
            # Format as SSE data
            yield f"data: {chunk}\n\n"
        # Send done event
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/erd/{analysis_id}")
async def chat_about_erd_analysis(
    analysis_id: int,
    request: ChatRequest,
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat about an ERD analysis.

    Streams responses using Server-Sent Events.
    """
    history = [{"role": m.role, "content": m.content} for m in request.history]

    return StreamingResponse(
        event_generator(
            stream_erd_chat,
            analysis_id,
            request.message,
            history,
            db,
            model=request.model,
            api_key=tamu_api_key,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/integrity/{analysis_id}")
async def chat_about_integrity_analysis(
    analysis_id: int,
    request: ChatRequest,
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat about an Integrity analysis.

    Streams responses using Server-Sent Events.
    """
    history = [{"role": m.role, "content": m.content} for m in request.history]

    return StreamingResponse(
        event_generator(
            stream_integrity_chat,
            analysis_id,
            request.message,
            history,
            db,
            model=request.model,
            api_key=tamu_api_key,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/models")
async def list_chat_models(
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
):
    """
    List available TAMU chat models for client-side selection.
    """
    try:
        models = await fetch_tamu_models(api_key=tamu_api_key)
        return {
            "models": models,
            "default_model": TAMU_DEFAULT_MODEL,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch models: {str(exc)}")
