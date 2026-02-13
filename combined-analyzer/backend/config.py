"""
Configuration module for the Combined Analyzer backend.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env file
load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./combined_analyzer.db")

# GitHub OAuth
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/github/callback")

# Encryption key for tokens (generate with Fernet.generate_key() and store in env)
ENCRYPTION_KEY = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

# Repository storage
REPOS_DIR = Path("uploads/repos")
REPOS_DIR.mkdir(parents=True, exist_ok=True)

# Upload limits
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

# Allowed archive types
ALLOWED_ARCHIVE_TYPES = [
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
]
