"""
Integrity Analysis Service

Single-prompt workflow for security integrity analysis:
1. One combined prompt evaluates all 6 characteristics + summary
2. Response is split into individual CharacteristicReport objects

Also exports shared utilities used by other analysis services.

Uses TAMU API (OpenAI-compatible) so the same API key as chat works.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.repository import Repository, DiscoveredFile, FileType
from services.chat_service import get_client, TAMU_DEFAULT_MODEL


def _extract_content_from_sse(sse_text: str) -> str:
    """If the response is SSE (multiple 'data: {...}' lines), concatenate all delta.content."""
    if not sse_text or not sse_text.strip():
        return ""
    out = []
    for line in sse_text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]" or not payload:
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            continue
        choices = obj.get("choices") if isinstance(obj, dict) else None
        if not choices or not isinstance(choices, list):
            continue
        first = choices[0] if choices else None
        if not isinstance(first, dict):
            continue
        delta = first.get("delta") or first.get("message") or {}
        if not isinstance(delta, dict):
            continue
        part = delta.get("content")
        if isinstance(part, str):
            out.append(part)
    return "".join(out) if out else ""


def _tamu_completion(
    api_key: Optional[str],
    prompt: str,
    max_tokens: int = 4096,
    model: Optional[str] = None,
) -> str:
    """Sync helper: call TAMU chat completion and return response text."""
    client = get_client(api_key=api_key)
    use_model = (model and model.strip()) or TAMU_DEFAULT_MODEL
    # Request non-streaming; some TAMU backends still return SSE
    resp = client.chat.completions.create(
        model=use_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        stream=False,
    )
    content = ""
    try:
        if isinstance(resp, str):
            content = resp
        elif getattr(resp, "choices", None) and resp.choices:
            msg = getattr(resp.choices[0], "message", None)
            if msg and getattr(msg, "content", None):
                content = msg.content or ""
            else:
                delta = getattr(resp.choices[0], "delta", None)
                if delta and getattr(delta, "content", None):
                    content = delta.content or ""
        if not content and isinstance(resp, str):
            content = resp
    except Exception as e:
        logger.exception("TAMU API response handling: %s", e)

    # If we got raw SSE (e.g. "data: {...}\n..."), extract and concatenate chunk contents
    if isinstance(content, str) and (content.strip().startswith("data:") or "\ndata:" in content):
        content = _extract_content_from_sse(content)
    if content:
        logger.info(
            "TAMU API response (content, first 1500 chars): %s",
            (content[:1500] + "..." if len(content) > 1500 else content),
        )
        return content
    logger.warning(
        "TAMU API returned empty or unexpected content. Check API key, TAMU_API_BASE, and TAMU_MODEL. See https://docs.tamus.ai/docs/prod/advanced/api/api-docs"
    )
    return ""


@dataclass
class CharacteristicReport:
    """Report for a single security characteristic."""
    characteristic: str
    score: float
    status: str
    description: str
    findings: List[Dict]
    recommendations: List[str]


@dataclass
class IntegrityAnalysisResult:
    """Complete integrity analysis result."""
    confidentiality: CharacteristicReport
    data_integrity: CharacteristicReport
    authenticity: CharacteristicReport
    non_repudiation: CharacteristicReport
    accountability: CharacteristicReport
    resistance: CharacteristicReport
    overall_score: float
    summary: Dict


def read_file_content(repo_path: str, file_path: str) -> str:
    """Read the full content of a file."""
    full_path = Path(repo_path) / file_path
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def parse_json_response(response_text: str) -> Dict:
    """Parse JSON from model response, handling markdown code blocks and surrounding text.
    Also unwraps TAMU/OpenAI-style responses that may nest JSON in 'content' or 'message'.
    """
    if not response_text or not isinstance(response_text, str):
        return {}
    text = response_text.strip()

    # Try to extract JSON from markdown code block
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()

    def try_parse(s: str) -> Dict:
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return {}

    obj = try_parse(text)
    if not obj:
        # Fallback: find first { and matching } to extract a JSON object from surrounding text
        start_brace = text.find("{")
        if start_brace >= 0:
            depth = 0
            for i in range(start_brace, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        obj = try_parse(text[start_brace : i + 1])
                        break

    # Unwrap nested JSON: some APIs return {"content": "{\"score\": ...}"} or similar
    for key in ("content", "message", "result", "data", "body"):
        if not obj or not isinstance(obj.get(key), str):
            continue
        inner = obj[key].strip()
        if (inner.startswith("{") and "}" in inner) or (inner.startswith("[") and "]" in inner):
            parsed = try_parse(inner)
            if parsed and isinstance(parsed, dict):
                # Prefer inner keys for our expected fields
                for k, v in parsed.items():
                    if k not in obj or obj[k] is None:
                        obj[k] = v
    return obj if isinstance(obj, dict) else {}


def _description_from_result(result: Dict, default: str) -> str:
    """Get description from result, trying common keys used by TAMU/LLM responses."""
    if not result:
        return default
    for key in ("description", "summary", "explanation", "assessment", "overview"):
        val = result.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return default


def _log_incomplete_response(characteristic: str, result: Dict, raw_preview: str) -> None:
    """Log when a characteristic analysis returned incomplete or unparseable data."""
    if not result or not result.get("description"):
        logger.warning(
            "Integrity analysis '%s' returned no description. Parsed keys: %s. Raw response (first 800 chars): %s",
            characteristic,
            list(result.keys()) if result else [],
            raw_preview[:800] if raw_preview else "(empty)",
        )


def prepare_file_contents(repo_path: str, files: List[Dict], limit: int = 30) -> List[Dict]:
    """Prepare file contents for analysis."""
    file_contents = []
    for f in files[:limit]:
        content = read_file_content(repo_path, f['file_path'])
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"
        file_contents.append({
            'path': f['file_path'],
            'content': content
        })
    return file_contents


async def load_user_stories_for_repo(
    repo_path: str, repository_id: int, db: AsyncSession
) -> str:
    """
    Load user story content for a repository from discovered files.
    Returns concatenated user stories text, or empty string if none found.
    """
    result = await db.execute(
        select(DiscoveredFile).where(
            DiscoveredFile.repository_id == repository_id,
            DiscoveredFile.file_type == FileType.user_story.value,
            DiscoveredFile.is_selected_erd == True,
        )
    )
    story_files = result.scalars().all()
    if not story_files:
        return ""

    all_stories = []
    for sf in story_files:
        full_path = Path(repo_path) / sf.file_path
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            all_stories.append(f"## From: {sf.file_path}\n\n{content}")
        except Exception:
            pass

    return "\n\n---\n\n".join(all_stories)


def build_user_stories_prompt_section(user_stories: str) -> str:
    """Build the user stories section to inject into analysis prompts."""
    if not user_stories.strip():
        return ""
    return f"""

## User Stories / Requirements Documentation:
The following user stories and/or acceptance criteria have been provided for this project. You MUST cross-reference the code against these requirements:

{user_stories}

## Additional Instructions for User Story Compliance:
- For each user story, check whether the code implements the described functionality.
- Flag any user stories that appear to be NOT implemented or only PARTIALLY implemented in the code.
- Flag any code that contradicts or violates the acceptance criteria.
- In your findings, reference the specific user story ID (e.g., US-01) when a finding relates to a requirement.
- In your recommendations, suggest what needs to be added or changed to satisfy unmet user stories.
"""


def _extract_characteristic(result: Dict, key: str, label: str) -> CharacteristicReport:
    """Extract a single characteristic report from the combined response."""
    data = result.get(key, {})
    if not isinstance(data, dict):
        data = {}
    return CharacteristicReport(
        characteristic=label,
        score=data.get("score", 50),
        status=data.get("status", "partially_fulfilled"),
        description=data.get("description", "Analysis incomplete"),
        findings=data.get("findings", []),
        recommendations=data.get("recommendations", []),
    )


async def run_integrity_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> IntegrityAnalysisResult:
    """Main orchestrator: Runs the complete integrity analysis in a single prompt."""
    repo_path = repository.local_path

    result = await db.execute(
        select(DiscoveredFile).where(
            DiscoveredFile.repository_id == repository.id,
            DiscoveredFile.is_selected_integrity == True
        )
    )
    files = result.scalars().all()

    if not files:
        raise ValueError("No files selected for integrity analysis")

    file_list = [{'file_path': f.file_path, 'file_type': f.file_type} for f in files]
    file_contents = prepare_file_contents(repo_path, file_list)

    prompt = f"""Analyze the following codebase for ISO 25010 SECURITY / INTEGRITY. Evaluate ALL SIX characteristics below in a single response.

## Characteristic 1: CONFIDENTIALITY
Whether unauthorized users cannot access private data.
Look for:
1. Access control mechanisms (role-based access, permissions)
2. Data encryption (at rest and in transit)
3. Secure storage of sensitive data (passwords, tokens, API keys)
4. Environment variable usage for secrets
5. Proper visibility/scope of sensitive functions and data
6. Session management and token handling

## Characteristic 2: DATA INTEGRITY
Whether data cannot be modified without authorization and validations prevent corruption.
Look for:
1. Input validation (type checking, format validation, range checks)
2. Data sanitization before storage
3. Database constraints and transactions
4. Immutability patterns where appropriate
5. Checksums or hashes for data verification
6. Proper error handling that prevents partial updates
7. Authorization checks before data modification

## Characteristic 3: AUTHENTICITY
Whether users are who they claim to be.
Look for:
1. Authentication mechanisms (OAuth, JWT, session-based, API keys)
2. Password hashing algorithms (bcrypt, argon2, etc.)
3. Multi-factor authentication support
4. Token validation and verification
5. Identity provider integration
6. Secure password reset flows
7. Session invalidation on logout

## Characteristic 4: NON-REPUDIATION
Whether actions are logged and traceable to specific users, preventing denial of actions.
Look for:
1. Audit logging with user identification
2. Timestamped action records
3. Digital signatures for critical operations
4. Immutable audit trails
5. Transaction logging
6. Request/response logging with user context

## Characteristic 5: ACCOUNTABILITY
Whether the system tracks who did what and when.
Look for:
1. User action logging
2. Created_by/updated_by fields in data models
3. Timestamp tracking (created_at, updated_at)
4. Change history/versioning
5. Activity feeds or history endpoints
6. User session tracking

## Characteristic 6: RESISTANCE
Whether the system resists common attacks.
Look for:
1. SQL Injection (parameterized queries, ORMs, raw SQL usage)
2. XSS (Cross-Site Scripting) - output encoding, CSP headers, sanitization
3. CSRF (Cross-Site Request Forgery) - token validation, SameSite cookies
4. Parameter tampering - server-side validation, type checking
5. Path traversal - file path validation
6. Command injection - shell command safety
7. Security headers (CORS, CSP, X-Frame-Options)

Files to analyze:
{json.dumps(file_contents, indent=2)}

IMPORTANT: Be thorough and detailed. For EACH characteristic, aim to provide 4 or more specific findings with actual code snippets and file paths. If there are genuinely fewer than 4 issues or observations to report for a characteristic, that is fine - do not fabricate findings. But do not cut short your analysis just to be brief. Give the same level of detail you would if analyzing each characteristic independently.

Respond with a single JSON object containing all six characteristic evaluations plus an overall summary. Weight Resistance and Confidentiality higher in the overall score:
{{
    "confidentiality": {{
        "score": <0-100>,
        "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
        "description": "<2-3 sentence summary>",
        "findings": [
            {{
                "type": "<positive|negative|warning>",
                "file_path": "<path>",
                "line_number": <number or null>,
                "code_snippet": "<relevant code>",
                "explanation": "<what this means>"
            }}
        ],
        "recommendations": ["<actionable recommendation>", ...]
    }},
    "data_integrity": {{ ... same structure ... }},
    "authenticity": {{ ... same structure ... }},
    "non_repudiation": {{ ... same structure ... }},
    "accountability": {{ ... same structure ... }},
    "resistance": {{ ... same structure ... }},
    "summary": {{
        "overall_score": <0-100 weighted average>,
        "risk_level": "<low|medium|high|critical>",
        "executive_summary": "<3-4 sentence overall assessment>",
        "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
        "areas_for_improvement": ["<area 1>", "<area 2>", "<area 3>"],
        "priority_recommendations": ["<most critical recommendation>", ...]
    }}
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 16384, model)
    result = parse_json_response(response_text)

    if not result:
        logger.warning("Integrity analysis returned no parseable result. Raw (first 800): %s", (response_text or "")[:800])

    confidentiality = _extract_characteristic(result, "confidentiality", "Confidentiality")
    data_integrity = _extract_characteristic(result, "data_integrity", "Data Integrity")
    authenticity = _extract_characteristic(result, "authenticity", "Authenticity")
    non_repudiation = _extract_characteristic(result, "non_repudiation", "Non-Repudiation")
    accountability = _extract_characteristic(result, "accountability", "Accountability")
    resistance = _extract_characteristic(result, "resistance", "Resistance")

    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return IntegrityAnalysisResult(
        confidentiality=confidentiality,
        data_integrity=data_integrity,
        authenticity=authenticity,
        non_repudiation=non_repudiation,
        accountability=accountability,
        resistance=resistance,
        overall_score=summary.get('overall_score', 50),
        summary=summary,
    )
