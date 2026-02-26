"""
Services for the Combined Analyzer.
"""

from .github_service import (
    get_github_auth_url,
    exchange_code_for_token,
    get_github_user,
    save_github_token,
    get_github_token,
    get_github_auth_status,
    list_github_repos,
    clone_github_repo,
    delete_github_token,
)
from .folder_service import (
    save_and_extract_zip,
    delete_repository_files,
)
from .discovery_service import run_file_discovery, run_discovery_only
from .erd_analysis_service import run_erd_analysis
from .integrity_analysis_service import run_integrity_analysis
from .compliance_analysis_service import run_compliance_analysis
from .correctness_analysis_service import run_correctness_analysis
from .usability_analysis_service import run_usability_analysis
from .maintainability_analysis_service import run_maintainability_analysis

__all__ = [
    # GitHub
    "get_github_auth_url",
    "exchange_code_for_token",
    "get_github_user",
    "save_github_token",
    "get_github_token",
    "get_github_auth_status",
    "list_github_repos",
    "clone_github_repo",
    "delete_github_token",
    # Folder
    "save_and_extract_zip",
    "delete_repository_files",
    # Discovery
    "run_file_discovery",
    "run_discovery_only",
    # Analysis
    "run_erd_analysis",
    "run_integrity_analysis",
    "run_compliance_analysis",
    "run_correctness_analysis",
    "run_usability_analysis",
    "run_maintainability_analysis",
]
