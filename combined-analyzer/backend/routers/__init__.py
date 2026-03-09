"""
API Routers for the Combined Analyzer.
"""

from .repositories import router as repositories_router
from .github import router as github_router
from .upload import router as upload_router
from .erd_analysis import router as erd_router
from .integrity_analysis import router as integrity_router
from .chat import router as chat_router
from .classes import router as classes_router

__all__ = [
    "repositories_router",
    "github_router",
    "upload_router",
    "erd_router",
    "integrity_router",
    "chat_router",
    "classes_router",
]
