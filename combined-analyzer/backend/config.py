"""
Configuration module for the Combined Analyzer backend.
"""

import os
import socket
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
from cryptography.fernet import Fernet

_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)


_raw_url = (os.getenv("DATABASE_URL") or "").strip()
_db_user = (os.getenv("DB_USER") or "").strip()
_db_password = (os.getenv("DB_PASSWORD") or "").strip()
_db_host = (os.getenv("DB_HOST") or "").strip()
_db_port = (os.getenv("DB_PORT") or "").strip()
_db_name = (os.getenv("DB_NAME") or "").strip()

def _postgres_url_to_async(url: str) -> str:
    url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg2://"):
        url = "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    if "ssl" not in url and ("supabase.co" in url or "pooler.supabase.com" in url):
        url += "&ssl=require" if "?" in url else "?ssl=require"
    return url

def _host_resolves(url: str) -> bool:
    """True if the URL's host can be resolved (DNS)."""
    try:
        # netloc is user:pass@host:port; host is after last @, before last :
        netloc = url.split("://", 1)[-1].split("/")[0]
        host_port = netloc.rpartition("@")[-1]
        host = host_port.rsplit(":", 1)[0].strip("[]")
        port = int(host_port.rsplit(":", 1)[-1]) if ":" in host_port else 5432
        socket.getaddrinfo(host, port)
        return True
    except Exception:
        return False

_use_postgres = False
if _raw_url and (_raw_url.startswith("postgresql://") or _raw_url.startswith("postgres://")):
    if _host_resolves(_raw_url):
        DATABASE_URL = _postgres_url_to_async(_raw_url)
        _use_postgres = True
    else:
        import warnings
        warnings.warn(
            "Supabase/Postgres host in DATABASE_URL could not be resolved (DNS). "
            "Using SQLite. To use Supabase: try the Session pooler (IPv4) from "
            "Dashboard → Connect → Connection string → Session mode."
        )
        DATABASE_URL = "sqlite+aiosqlite:///./combined_analyzer.db"
elif all((_db_user, _db_password, _db_host, _db_port, _db_name)):
    try:
        socket.getaddrinfo(_db_host, int(_db_port))
        _use_postgres = True
        _user = quote_plus(_db_user)
        _password = quote_plus(_db_password)
        DATABASE_URL = f"postgresql+asyncpg://{_user}:{_password}@{_db_host}:{_db_port}/{_db_name}?ssl=require"
    except (socket.gaierror, ValueError, OSError):
        import warnings
        warnings.warn(
            f"Cannot resolve DB_HOST '{_db_host}'. Using SQLite. "
            "For Supabase use Session pooler (IPv4) from Dashboard → Connect."
        )
        DATABASE_URL = "sqlite+aiosqlite:///./combined_analyzer.db"
else:
    DATABASE_URL = _raw_url or "sqlite+aiosqlite:///./combined_analyzer.db"

# For startup log and /api/health: "postgres" when using Supabase, "sqlite" otherwise
DATABASE_KIND = "postgres" if _use_postgres else "sqlite"

# Frontend URL (for OAuth callback redirects)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

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
