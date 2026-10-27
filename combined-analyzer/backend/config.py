"""Validated configuration for the PostgreSQL/Supabase application."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

load_dotenv(Path(__file__).resolve().parent / ".env")


def _required(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is required; see combined-analyzer/README.md")
    return value


def _database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        url = make_url(raw.replace("postgres://", "postgresql://", 1))
    else:
        url = URL.create(
            "postgresql",
            username=_required("DB_USER"),
            password=_required("DB_PASSWORD"),
            host=_required("DB_HOST"),
            port=int(_required("DB_PORT")),
            database=_required("DB_NAME"),
        )
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("DATABASE_URL must use PostgreSQL; SQLite is not supported")
    url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    if "sslmode" in query:
        query["ssl"] = query.pop("sslmode")
    if "ssl" not in query and url.host and (
        url.host.endswith(".supabase.co") or url.host.endswith(".supabase.com")
    ):
        query["ssl"] = "require"
    return url.set(query=query).render_as_string(hide_password=False)


DATABASE_URL = _database_url()
DATABASE_KIND = "postgres"
SUPABASE_URL = _required("SUPABASE_URL").rstrip("/")
SUPABASE_ANON_KEY = _required("SUPABASE_ANON_KEY")
_auth_url = urlsplit(SUPABASE_URL)
if _auth_url.scheme != "https" and not (
    _auth_url.scheme == "http" and _auth_url.hostname in {"localhost", "127.0.0.1", "::1"}
):
    raise RuntimeError("SUPABASE_URL must use HTTPS (HTTP is allowed only on localhost)")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:8000/api/github/callback"
)

# The same key must be supplied to every restart. Never generate an ephemeral key.
ENCRYPTION_KEY = _required("GITHUB_TOKEN_ENCRYPTION_KEY")
try:
    Fernet(ENCRYPTION_KEY.encode("ascii"))
except (ValueError, UnicodeEncodeError) as exc:
    raise RuntimeError("GITHUB_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc

# Render mounts this path on a persistent disk; local development uses uploads/repos.
REPOS_DIR = Path(os.getenv("REPOS_DIR", "uploads/repos")).resolve()
REPOS_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024
MAX_ANALYSIS_SOURCE_BYTES = 200_000
ALLOWED_ARCHIVE_TYPES = [
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
]
