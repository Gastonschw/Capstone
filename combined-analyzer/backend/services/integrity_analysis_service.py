"""
Integrity Analysis Service

Multi-agent workflow for security integrity analysis:
1. File Discovery - identify security-relevant files
2. 6 Characteristic Agents - analyze each security characteristic
3. Summary Agent - generate overall assessment

Uses TAMU API (OpenAI-compatible) so the same API key as chat works.
"""

import asyncio
import json
import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository, FileType
from config import MAX_ANALYSIS_SOURCE_BYTES
from services.chat_service import get_client, TAMU_DEFAULT_MODEL


def _extract_content_from_sse(sse_text: str) -> str:
    """Decode a complete provider stream without silently discarding errors."""
    out = []
    stopped = False
    for line in sse_text.splitlines():
        line = line.strip()
        if not line or line.startswith(":"):
            continue
        if not line.startswith("data:"):
            raise ValueError("Malformed analysis stream")
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except ValueError as exc:
            raise ValueError("Malformed analysis stream JSON") from exc
        if not isinstance(obj, dict) or obj.get("error"):
            raise ValueError("Analysis provider stream failed")
        choices = obj.get("choices")
        if choices == [] and obj.get("usage"):
            continue
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ValueError("Analysis stream requires a choice")
        first = choices[0]
        reason = first.get("finish_reason")
        if reason is not None:
            if reason != "stop":
                raise ValueError("Analysis provider did not finish its response")
            stopped = True
        delta = first.get("delta") or first.get("message") or {}
        if not isinstance(delta, dict) or delta.get("refusal"):
            raise ValueError("Invalid analysis stream content")
        part = delta.get("content")
        if part is not None:
            if not isinstance(part, str):
                raise ValueError("Invalid analysis stream text")
            out.append(part)
    if not stopped or not out:
        raise ValueError("Incomplete or empty analysis stream")
    return "".join(out)


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
    if isinstance(resp, str):
        content = resp
    elif getattr(resp, "choices", None):
        choice = resp.choices[0]
        if getattr(choice, "finish_reason", None) != "stop":
            raise ValueError("Analysis provider did not finish its response")
        message = getattr(choice, "message", None)
        if message is not None and not getattr(message, "refusal", None):
            content = getattr(message, "content", "")

    # If we got raw SSE (e.g. "data: {...}\n..."), extract and concatenate chunk contents
    if isinstance(content, str) and (content.strip().startswith("data:") or "\ndata:" in content):
        content = _extract_content_from_sse(content)
    if isinstance(content, str) and content.strip():
        return content
    raise ValueError("Analysis provider returned empty content")


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




def parse_json_response(response_text: str) -> Dict:
    """Decode one JSON object, optionally enclosed in a Markdown fence."""
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Analysis provider returned empty content")
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].strip() not in ("```", "```json") or lines[-1].strip() != "```":
            raise ValueError("Invalid fenced analysis response")
        text = "\n".join(lines[1:-1])
    try:
        result = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("Analysis provider returned invalid JSON") from exc
    if not isinstance(result, dict) or not result:
        raise ValueError("Analysis response must be a nonempty JSON object")
    return result


def _required_text(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Analysis response requires nonempty {field}")


def _required_strings(value: Any, field: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"Analysis response requires a {field} list")
    for item in value:
        _required_text(item, field)


def _required_score(value: Any, field: str) -> None:
    if type(value) not in (int, float) or not 0 <= value <= 100 or not math.isfinite(value):
        raise ValueError(f"Analysis {field} must be a finite number from 0 to 100")


def validate_characteristic_response(result: Dict) -> Dict:
    _required_score(result.get("score"), "score")
    if result.get("status") not in ("fulfilled", "partially_fulfilled", "not_fulfilled", "not_applicable"):
        raise ValueError("Invalid analysis status")
    _required_text(result.get("description"), "description")
    _required_strings(result.get("recommendations"), "recommendations")
    findings = result.get("findings")
    if not isinstance(findings, list):
        raise ValueError("Analysis response requires a findings list")
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Analysis findings must be objects")
        if finding.get("type") not in ("positive", "negative", "warning"):
            raise ValueError("Invalid finding type")
        _required_text(finding.get("file_path"), "finding file_path")
        _required_text(finding.get("explanation"), "finding explanation")
        if "line_number" not in finding or (finding["line_number"] is not None and
                (type(finding["line_number"]) is not int or finding["line_number"] < 1)):
            raise ValueError("Invalid finding line_number")
        if not isinstance(finding.get("code_snippet"), str):
            raise ValueError("Finding requires code_snippet")
    return result


def validate_summary_response(result: Dict) -> Dict:
    _required_score(result.get("overall_score"), "overall_score")
    if result.get("risk_level") not in ("low", "medium", "high", "critical"):
        raise ValueError("Invalid analysis risk_level")
    _required_text(result.get("executive_summary"), "executive_summary")
    for field in ("strengths", "areas_for_improvement", "priority_recommendations"):
        _required_strings(result.get(field), field)
    return result


class PreparedFiles(list):
    """Already read and bounded sources shared by the characteristic agents."""


def validate_selected_files(repo_path: str, selected_files: Optional[List[Dict]]) -> PreparedFiles:
    """Preflight the entire snapshot before any provider request."""
    if not isinstance(selected_files, list) or not selected_files:
        raise ValueError("A nonempty selected-files snapshot is required")
    root = Path(repo_path).resolve(strict=True)
    total = 0
    prepared = PreparedFiles()
    for source in selected_files:
        if not isinstance(source, dict):
            raise ValueError("Invalid selected-files snapshot")
        name = source.get("file_path")
        file_type = source.get("file_type")
        if not isinstance(name, str) or not name or not isinstance(file_type, str) or not file_type:
            raise ValueError("Snapshot requires file_path and file_type")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Selected source must be a repository-relative path")
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Invalid selected source: {name}")
        size = path.stat().st_size
        if total + size > MAX_ANALYSIS_SOURCE_BYTES:
            raise ValueError(f"Selected sources exceed {MAX_ANALYSIS_SOURCE_BYTES} bytes")
        with path.open("rb") as stream:
            data = stream.read(MAX_ANALYSIS_SOURCE_BYTES - total + 1)
        total += len(data)
        if total > MAX_ANALYSIS_SOURCE_BYTES:
            raise ValueError(f"Selected sources exceed {MAX_ANALYSIS_SOURCE_BYTES} bytes")
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Selected source is not UTF-8 text: {name}") from exc
        prepared.append({"path": name, "content": content, "file_type": file_type})
    if not any(source["content"].strip() for source in prepared):
        raise ValueError("Selected sources contain no analysis content")
    return prepared


def prepare_file_contents(repo_path: str, files: List[Dict]) -> List[Dict]:
    """Preserve every source in full; orchestrators reuse their preflight read."""
    return files if isinstance(files, PreparedFiles) else validate_selected_files(repo_path, files)


def snapshot_user_stories(files: List[Dict]) -> str:
    return "\n\n---\n\n".join(
        f"## From: {source['path']}\n\n{source['content']}"
        for source in files if source["file_type"] == FileType.user_story.value
    )


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


async def analyze_confidentiality(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """
    Analyze whether unauthorized users cannot access private data.
    """
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for CONFIDENTIALITY - whether unauthorized users cannot access private data.

Look for:
1. Access control mechanisms (role-based access, permissions)
2. Data encryption (at rest and in transit)
3. Secure storage of sensitive data (passwords, tokens, API keys)
4. Environment variable usage for secrets
5. Proper visibility/scope of sensitive functions and data
6. Session management and token handling

For each finding, provide:
- The specific file and line number (if identifiable)
- A relevant code snippet (max 5 lines)
- Explanation of whether it supports or undermines confidentiality

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of confidentiality posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for confidentiality>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = validate_characteristic_response(parse_json_response(response_text))
    
    description = result['description']
    

    return CharacteristicReport(
        characteristic="Confidentiality",
        score=result["score"],
        status=result["status"],
        description=description,
        findings=result["findings"],
        recommendations=result["recommendations"]
    )


async def analyze_data_integrity(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """
    Analyze whether data cannot be modified without authorization.
    """
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for DATA INTEGRITY - whether data cannot be modified without authorization and validations prevent corruption.

Look for:
1. Input validation (type checking, format validation, range checks)
2. Data sanitization before storage
3. Database constraints and transactions
4. Immutability patterns where appropriate
5. Checksums or hashes for data verification
6. Proper error handling that prevents partial updates
7. Authorization checks before data modification

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of data integrity posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for data integrity>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = validate_characteristic_response(parse_json_response(response_text))
    
    description = result['description']
    

    return CharacteristicReport(
        characteristic="Data Integrity",
        score=result['score'],
        status=result['status'],
        description=description,
        findings=result["findings"],
        recommendations=result["recommendations"]
    )


async def analyze_authenticity(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """
    Analyze whether users are who they claim to be.
    """
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for AUTHENTICITY - whether users are who they claim to be.

Look for:
1. Authentication mechanisms (OAuth, JWT, session-based, API keys)
2. Password hashing algorithms (bcrypt, argon2, etc.)
3. Multi-factor authentication support
4. Token validation and verification
5. Identity provider integration
6. Secure password reset flows
7. Session invalidation on logout

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of authenticity posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for authenticity>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = validate_characteristic_response(parse_json_response(response_text))
    
    description = result['description']
    

    return CharacteristicReport(
        characteristic="Authenticity",
        score=result["score"],
        status=result["status"],
        description=description,
        findings=result["findings"],
        recommendations=result["recommendations"]
    )


async def analyze_non_repudiation(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """
    Analyze whether actions are logged and traceable to specific users.
    """
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for NON-REPUDIATION - whether actions are logged and traceable to specific users, preventing denial of actions.

Look for:
1. Audit logging with user identification
2. Timestamped action records
3. Digital signatures for critical operations
4. Immutable audit trails
5. Transaction logging
6. Request/response logging with user context
7. Event sourcing patterns

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of non-repudiation posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for non-repudiation>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = validate_characteristic_response(parse_json_response(response_text))
    
    description = result['description']
    

    return CharacteristicReport(
        characteristic="Non-Repudiation",
        score=result["score"],
        status=result["status"],
        description=description,
        findings=result["findings"],
        recommendations=result["recommendations"]
    )


async def analyze_accountability(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """
    Analyze whether the system tracks who did what and when.
    """
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for ACCOUNTABILITY - whether the system tracks who did what and when.

Look for:
1. User action logging
2. Created_by/updated_by fields in data models
3. Timestamp tracking (created_at, updated_at)
4. Change history/versioning
5. Activity feeds or history endpoints
6. User session tracking
7. Administrative action logging

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of accountability posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for accountability>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = validate_characteristic_response(parse_json_response(response_text))
    
    description = result['description']
    

    return CharacteristicReport(
        characteristic="Accountability",
        score=result["score"],
        status=result["status"],
        description=description,
        findings=result["findings"],
        recommendations=result["recommendations"]
    )


async def analyze_resistance(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """
    Analyze whether the system resists common attacks.
    """
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for RESISTANCE - whether the system resists common attacks.

Look for vulnerabilities and protections against:
1. SQL Injection (parameterized queries, ORMs, raw SQL usage)
2. XSS (Cross-Site Scripting) - output encoding, CSP headers, sanitization
3. CSRF (Cross-Site Request Forgery) - token validation, SameSite cookies
4. Parameter tampering - server-side validation, type checking
5. Path traversal - file path validation
6. Command injection - shell command safety
7. Insecure deserialization
8. Security headers (CORS, CSP, X-Frame-Options)

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of attack resistance posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for attack resistance>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = validate_characteristic_response(parse_json_response(response_text))
    
    description = result['description']
    

    return CharacteristicReport(
        characteristic="Resistance",
        score=result["score"],
        status=result["status"],
        description=description,
        findings=result["findings"],
        recommendations=result["recommendations"]
    )


async def generate_summary(
    reports: List[CharacteristicReport], api_key: Optional[str] = None, model: Optional[str] = None
) -> Dict:
    """
    Generate an overall summary based on all characteristic analyses.
    """
    reports_data = []
    for r in reports:
        reports_data.append({
            'characteristic': r.characteristic,
            'score': r.score,
            'status': r.status,
            'description': r.description,
            'finding_count': len(r.findings),
            'positive_findings': len([f for f in r.findings if f.get('type') == 'positive']),
            'negative_findings': len([f for f in r.findings if f.get('type') == 'negative']),
            'recommendation_count': len(r.recommendations)
        })

    prompt = f"""Based on the following integrity analysis results, generate an executive summary.

Analysis Results:
{json.dumps(reports_data, indent=2)}

Provide:
1. An overall integrity score (weighted average, with Resistance and Confidentiality weighted higher)
2. A brief executive summary (3-4 sentences)
3. Top 3 strengths of the system
4. Top 3 areas for improvement
5. Overall risk level (low, medium, high, critical)

Respond with a JSON object:
{{
    "overall_score": <0-100>,
    "risk_level": "<low|medium|high|critical>",
    "executive_summary": "<3-4 sentence summary>",
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "areas_for_improvement": ["<area 1>", "<area 2>", "<area 3>"],
    "priority_recommendations": ["<most critical recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 2048, model)
    return validate_summary_response(parse_json_response(response_text))


async def run_integrity_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    selected_files: Optional[List[Dict]] = None,
) -> IntegrityAnalysisResult:
    """
    Main orchestrator: Runs the complete integrity analysis workflow.
    Uses TAMU API with api_key (or env fallback).
    """
    repo_path = repository.local_path

    file_list = validate_selected_files(repo_path, selected_files)

    # Run all characteristic analyses (TAMU API)
    confidentiality = await analyze_confidentiality(repo_path, file_list, api_key, model)
    data_integrity = await analyze_data_integrity(repo_path, file_list, api_key, model)
    authenticity = await analyze_authenticity(repo_path, file_list, api_key, model)
    non_repudiation = await analyze_non_repudiation(repo_path, file_list, api_key, model)
    accountability = await analyze_accountability(repo_path, file_list, api_key, model)
    resistance = await analyze_resistance(repo_path, file_list, api_key, model)

    # Generate summary
    all_reports = [confidentiality, data_integrity, authenticity, non_repudiation, accountability, resistance]
    summary = await generate_summary(all_reports, api_key, model)

    return IntegrityAnalysisResult(
        confidentiality=confidentiality,
        data_integrity=data_integrity,
        authenticity=authenticity,
        non_repudiation=non_repudiation,
        accountability=accountability,
        resistance=resistance,
        overall_score=summary['overall_score'],
        summary=summary
    )
