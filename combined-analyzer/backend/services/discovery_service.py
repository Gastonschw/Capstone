"""
Combined File Discovery Service

Discovers files for both ERD Analysis and Integrity Analysis.
Uses AI to identify:
- ERD images and user story files (for ERD analysis)
- Code, config, and documentation files (for Integrity analysis)

Uses TAMU API (OpenAI-compatible) so the same API key as chat works for discovery.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.repository import Repository, DiscoveredFile, FileType
from services.chat_service import get_client, TAMU_DEFAULT_MODEL


# ============== File Type Detection ==============

# Image extensions for ERD detection
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}

# Text file extensions for user story detection
TEXT_EXTENSIONS = {'.md', '.txt', '.rst', '.feature', '.story', '.adoc'}

# Code extensions for Integrity analysis
CODE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.cs': 'csharp',
    '.go': 'go',
    '.rb': 'ruby',
    '.php': 'php',
    '.rs': 'rust',
    '.cpp': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.hpp': 'cpp',
}

# Config extensions
CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.env', '.config'}

# Directories likely to contain ERD diagrams
ERD_DIRECTORY_HINTS = {
    'diagrams', 'erd', 'database', 'db', 'schema', 'models',
    'docs', 'documentation', 'design', 'architecture'
}

# Directories likely to contain user stories
STORY_DIRECTORY_HINTS = {
    'stories', 'user-stories', 'userstories', 'requirements',
    'specs', 'features', 'docs', 'documentation'
}

# Security-relevant keywords for Integrity analysis
SECURITY_KEYWORDS = {
    'auth', 'login', 'password', 'token', 'jwt', 'oauth', 'session',
    'encrypt', 'decrypt', 'hash', 'secret', 'key', 'credential',
    'permission', 'role', 'access', 'grant', 'deny', 'authorize',
    'sanitize', 'validate', 'escape', 'filter', 'input',
    'log', 'audit', 'track', 'monitor', 'record',
    'sql', 'query', 'database', 'inject', 'xss', 'csrf',
    'secure', 'security', 'protect', 'guard', 'middleware'
}


@dataclass
class FileCandidate:
    """A file candidate for analysis."""
    path: str
    file_type: str
    confidence: int = 50
    relevance: int = 50
    language: Optional[str] = None
    preview: Optional[str] = None


# ============== ERD File Scoring ==============

def score_erd_candidate(file_path: str) -> int:
    """Score how likely a file is an ERD diagram based on path and name."""
    path_parts = Path(file_path).parts

    score = 50  # Base score for any image

    # Check directory hints
    for part in path_parts[:-1]:
        if part.lower() in ERD_DIRECTORY_HINTS:
            score += 20
            break

    # Check filename hints
    filename = Path(file_path).stem.lower()
    erd_keywords = ['erd', 'entity', 'relationship', 'database', 'schema', 'diagram', 'db', 'model', 'data']

    for keyword in erd_keywords:
        if keyword in filename:
            score += 15
            break

    # Boost if in root or docs folder
    if len(path_parts) <= 2:
        score += 10

    return min(score, 100)


def score_user_story_candidate(file_path: str, content: str) -> int:
    """Score how likely a file contains user stories."""
    path_parts = Path(file_path).parts

    score = 30  # Base score for any text file

    # Check directory hints
    for part in path_parts[:-1]:
        if part.lower() in STORY_DIRECTORY_HINTS:
            score += 15
            break

    # Check filename hints
    filename = Path(file_path).stem.lower()
    story_keywords = ['story', 'stories', 'requirement', 'feature', 'user', 'acceptance', 'spec']

    for keyword in story_keywords:
        if keyword in filename:
            score += 15
            break

    # Content analysis
    content_lower = content.lower()

    # User story patterns
    if 'as a ' in content_lower and ' i want ' in content_lower:
        score += 25
    elif 'as a ' in content_lower:
        score += 15

    # Gherkin patterns
    if 'given ' in content_lower and 'when ' in content_lower and 'then ' in content_lower:
        score += 25

    # Acceptance criteria patterns
    if 'acceptance criteria' in content_lower:
        score += 20

    # Common requirement keywords
    requirement_keywords = ['shall', 'must', 'should', 'requirement', 'feature', 'scenario']
    for keyword in requirement_keywords:
        if keyword in content_lower:
            score += 5
            break

    return min(score, 100)


# ============== Integrity File Scoring ==============

def calculate_relevance_score(file_path: str, content: str) -> int:
    """Calculate security relevance score for Integrity analysis."""
    score = 50  # Base score

    path_lower = file_path.lower()
    content_lower = content.lower()

    # Boost for security-related paths
    security_paths = ['auth', 'security', 'middleware', 'guard', 'permission', 'login', 'session']
    for term in security_paths:
        if term in path_lower:
            score += 15
            break

    # Boost for configuration files
    if any(ext in path_lower for ext in ['.env', 'config', 'settings']):
        score += 10

    # Count security keywords in content
    keyword_count = sum(1 for kw in SECURITY_KEYWORDS if kw in content_lower)
    score += min(keyword_count * 3, 30)  # Max 30 points from keywords

    # Penalize test files
    if 'test' in path_lower or 'spec' in path_lower or 'mock' in path_lower:
        score -= 20

    # Penalize vendor directories
    if 'node_modules' in path_lower or 'vendor' in path_lower or '__pycache__' in path_lower:
        score = 0

    return max(0, min(100, score))


# ============== File Discovery ==============

def scan_repository_files(repo_path: str) -> Dict[str, List[Dict]]:
    """
    Scan a repository and categorize files by type.

    Returns dict with:
    - 'images': potential ERD images
    - 'text_files': potential user story files
    - 'code_files': code files for integrity analysis
    - 'config_files': config files for integrity analysis
    """
    repo = Path(repo_path)

    images = []
    text_files = []
    code_files = []
    config_files = []

    # Directories to skip
    skip_dirs = {
        'node_modules', 'vendor', '__pycache__', 'venv', '.venv',
        'dist', 'build', 'target', '.git', '.idea', '.vscode'
    }

    for root, dirs, files in os.walk(repo):
        # Filter out skip directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]

        for file in files:
            if file.startswith('.'):
                continue

            file_path = Path(root) / file
            rel_path = str(file_path.relative_to(repo))
            suffix = file_path.suffix.lower()

            # Read content for text-based files
            content = ""
            if suffix in TEXT_EXTENSIONS or suffix in CODE_EXTENSIONS or suffix in CONFIG_EXTENSIONS:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(5000).replace('\x00', '')  # Read first 5KB, strip null bytes
                except Exception:
                    continue

            # Categorize file
            if suffix in IMAGE_EXTENSIONS:
                images.append({
                    'path': rel_path,
                    'confidence': score_erd_candidate(rel_path)
                })
            elif suffix in TEXT_EXTENSIONS:
                text_files.append({
                    'path': rel_path,
                    'confidence': score_user_story_candidate(rel_path, content),
                    'preview': content[:500] if content else None
                })
            elif suffix in CODE_EXTENSIONS:
                code_files.append({
                    'path': rel_path,
                    'language': CODE_EXTENSIONS[suffix],
                    'relevance': calculate_relevance_score(rel_path, content),
                    'preview': content[:500] if content else None
                })
            elif suffix in CONFIG_EXTENSIONS:
                config_files.append({
                    'path': rel_path,
                    'relevance': calculate_relevance_score(rel_path, content),
                    'preview': content[:500] if content else None
                })

    return {
        'images': images,
        'text_files': text_files,
        'code_files': code_files,
        'config_files': config_files
    }


async def discover_files_with_ai(
    repo_path: str,
    images: List[Dict],
    text_files: List[Dict],
    api_key: Optional[str] = None,
) -> Dict[str, List[FileCandidate]]:
    """
    Use AI to intelligently identify ERD images and user story files.
    Uses TAMU API (OpenAI-compatible) with the given api_key (or env fallback).
    """
    client = get_client(api_key=api_key)

    # Prepare file list for AI analysis
    file_info = []
    for img in images[:50]:  # Limit to 50 images
        file_info.append({"path": img['path'], "type": "image"})

    for txt in text_files[:30]:  # Limit to 30 text files
        file_info.append({
            "path": txt['path'],
            "type": "text",
            "preview": txt.get('preview', '')[:200]
        })

    # Use AI to identify relevant files
    discovery_prompt = f"""You are analyzing a software project repository to find:
1. ERD (Entity-Relationship Diagram) images - visual diagrams showing database structure
2. User Story files - documents containing user requirements in formats like:
   - "As a [user], I want [feature] so that [benefit]"
   - Gherkin format (Given/When/Then)
   - Acceptance criteria lists

Here are the files in the repository:

## Image Files:
{json.dumps([f["path"] for f in file_info if f["type"] == "image"], indent=2)}

## Text Files with Previews:
{json.dumps([{"path": f["path"], "preview": f.get("preview", "")[:200]} for f in file_info if f["type"] == "text"], indent=2)}

Analyze these files and return a JSON object identifying which files are most likely ERD diagrams and user stories:

{{
    "erd_images": [
        {{"path": "path/to/image.png", "confidence": 85, "reason": "brief reason"}}
    ],
    "user_story_files": [
        {{"path": "path/to/file.md", "confidence": 90, "reason": "brief reason"}}
    ]
}}

Only include files you're reasonably confident about (confidence > 50).
Return ONLY the JSON object, no other text."""

    def _call_completion():
        resp = client.chat.completions.create(
            model=TAMU_DEFAULT_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": discovery_prompt}],
            temperature=0,
        )
        # TAMU/OpenAI may return an object with .choices, or in some cases a dict/str
        if isinstance(resp, str):
            return ""
        if isinstance(resp, dict):
            choices = resp.get("choices") or []
            if choices:
                first = choices[0]
                msg = first.get("message", first) if isinstance(first, dict) else getattr(first, "message", None)
                if isinstance(msg, dict):
                    return msg.get("content") or ""
                if msg and getattr(msg, "content", None):
                    return msg.content
            return ""
        if getattr(resp, "choices", None) and resp.choices:
            msg = getattr(resp.choices[0], "message", None)
            if msg and getattr(msg, "content", None):
                return msg.content
        return ""

    try:
        response_text = await asyncio.to_thread(_call_completion)
    except Exception:
        response_text = ""
    if not isinstance(response_text, str):
        response_text = ""

    try:
        # Parse JSON response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        ai_results = json.loads(response_text.strip())
    except json.JSONDecodeError:
        ai_results = {"erd_images": [], "user_story_files": []}

    # Build final candidates with AI and heuristic scores
    erd_candidates = []
    for item in ai_results.get("erd_images", []):
        erd_candidates.append(FileCandidate(
            path=item["path"],
            file_type=FileType.erd_image.value,
            confidence=item.get("confidence", 70)
        ))

    # Add high-scoring heuristic candidates not found by AI
    for img in images:
        if img['confidence'] >= 70 and not any(c.path == img['path'] for c in erd_candidates):
            erd_candidates.append(FileCandidate(
                path=img['path'],
                file_type=FileType.erd_image.value,
                confidence=img['confidence']
            ))

    story_candidates = []
    for item in ai_results.get("user_story_files", []):
        # Get preview from original text_files
        preview = ""
        for txt in text_files:
            if txt['path'] == item["path"]:
                preview = txt.get('preview', '')[:500]
                break

        story_candidates.append(FileCandidate(
            path=item["path"],
            file_type=FileType.user_story.value,
            confidence=item.get("confidence", 70),
            preview=preview
        ))

    # Add high-scoring heuristic candidates
    for txt in text_files:
        if txt['confidence'] >= 65 and not any(c.path == txt['path'] for c in story_candidates):
            story_candidates.append(FileCandidate(
                path=txt['path'],
                file_type=FileType.user_story.value,
                confidence=txt['confidence'],
                preview=txt.get('preview', '')[:500]
            ))

    # Sort by confidence
    erd_candidates.sort(key=lambda x: x.confidence, reverse=True)
    story_candidates.sort(key=lambda x: x.confidence, reverse=True)

    return {
        "erd_images": erd_candidates[:10],
        "user_story_files": story_candidates[:15]
    }


async def run_file_discovery(
    repo_path: str,
    db: AsyncSession,
    repository_id: int,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the complete file discovery workflow and save results to database.

    Discovers files for both ERD and Integrity analysis.
    Uses TAMU API when api_key is provided (or from env); same key as chat.
    """
    # Step 1: Scan for all files
    files = scan_repository_files(repo_path)

    # Step 2: Use AI + heuristics to identify ERD-related files
    discovered_erd = await discover_files_with_ai(
        repo_path,
        files['images'],
        files['text_files'],
        api_key=api_key,
    )

    # Step 3: Save all discovered files to database
    saved_files = []

    # Save ERD images
    for candidate in discovered_erd['erd_images']:
        db_file = DiscoveredFile(
            repository_id=repository_id,
            file_path=candidate.path,
            file_type=candidate.file_type,
            confidence_score=candidate.confidence,
            is_selected_erd=candidate.confidence >= 60,
            is_selected_integrity=False
        )
        db.add(db_file)
        saved_files.append(db_file)

    # Save user story files
    for candidate in discovered_erd['user_story_files']:
        db_file = DiscoveredFile(
            repository_id=repository_id,
            file_path=candidate.path,
            file_type=candidate.file_type,
            confidence_score=candidate.confidence,
            content_preview=candidate.preview,
            is_selected_erd=candidate.confidence >= 60,
            is_selected_integrity=False
        )
        db.add(db_file)
        saved_files.append(db_file)

    # Save code files (for Integrity analysis)
    for code_file in sorted(files['code_files'], key=lambda x: x['relevance'], reverse=True)[:100]:
        # Skip if relevance is too low
        if code_file['relevance'] < 10:
            continue

        db_file = DiscoveredFile(
            repository_id=repository_id,
            file_path=code_file['path'],
            file_type=FileType.code.value,
            language=code_file.get('language'),
            relevance_score=code_file['relevance'],
            content_preview=code_file.get('preview'),
            is_selected_erd=False,
            is_selected_integrity=code_file['relevance'] >= 50
        )
        db.add(db_file)
        saved_files.append(db_file)

    # Save config files (for Integrity analysis)
    for config_file in sorted(files['config_files'], key=lambda x: x['relevance'], reverse=True)[:20]:
        if config_file['relevance'] < 10:
            continue

        db_file = DiscoveredFile(
            repository_id=repository_id,
            file_path=config_file['path'],
            file_type=FileType.config.value,
            relevance_score=config_file['relevance'],
            content_preview=config_file.get('preview'),
            is_selected_erd=False,
            is_selected_integrity=config_file['relevance'] >= 50
        )
        db.add(db_file)
        saved_files.append(db_file)

    await db.commit()

    return {
        "erd_images_found": len(discovered_erd['erd_images']),
        "user_story_files_found": len(discovered_erd['user_story_files']),
        "code_files_found": len([f for f in saved_files if f.file_type == FileType.code.value]),
        "config_files_found": len([f for f in saved_files if f.file_type == FileType.config.value]),
        "total_files_scanned": sum(len(v) for v in files.values())
    }


async def run_discovery_only(repository: Repository, db: AsyncSession) -> Dict[str, Any]:
    """
    Run only the file discovery step without full analysis.
    Clears existing files and rediscovers.
    """
    # Clear existing discovered files
    await db.execute(
        delete(DiscoveredFile).where(DiscoveredFile.repository_id == repository.id)
    )
    await db.commit()

    # Run discovery
    return await run_file_discovery(repository.local_path, db, repository.id)
