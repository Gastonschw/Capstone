"""
Chat Service

Provides streaming chat capabilities for discussing analysis results.
Builds context from analysis data and original source files.
Uses TAMU API (OpenAI-compatible) for LLM responses.
"""

import os
import base64
import json
from pathlib import Path
from typing import List, Dict, Any, AsyncGenerator, Optional

import httpx
from openai import AsyncOpenAI, OpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from models.repository import Repository, FileType
from types import SimpleNamespace
from models.erd_analysis import ERDAnalysis
from models.integrity_analysis import IntegrityAnalysis
from models.compliance_analysis import ComplianceAnalysis
from models.correctness_analysis import CorrectnessAnalysis
from models.usability_analysis import UsabilityAnalysis
from models.maintainability_analysis import MaintainabilityAnalysis
from config import MAX_ANALYSIS_SOURCE_BYTES

load_dotenv()

# TAMU API configuration
TAMU_API_KEY = os.getenv("TAMU_API_KEY")
TAMU_API_BASE = os.getenv("TAMU_API_BASE", "https://chat-api.tamu.ai/api/v1")
TAMU_MODELS_URL = os.getenv("TAMU_MODELS_URL", "https://chat-api.tamu.ai/openai/models")
TAMU_DEFAULT_MODEL = os.getenv("TAMU_MODEL", "protected.Claude Opus 4.5")
MARKDOWN_OUTPUT_POLICY = """## Output Format Requirements
- Use markdown for structure and readability.
- Prefer short headings, bullet points, and numbered lists when useful.
- Use code fences for code examples and inline code backticks for identifiers/paths.
- Keep responses concise and scannable.
"""


def resolve_api_key(api_key: Optional[str] = None) -> str:
    """Resolve API key from request override or environment."""
    resolved_api_key = api_key or TAMU_API_KEY
    if not resolved_api_key:
        raise ValueError("TAMU API key is not configured")
    return resolved_api_key


def get_client(api_key: Optional[str] = None):
    """Synchronous client for analysis calls executed in worker threads."""
    return OpenAI(
        api_key=resolve_api_key(api_key),
        base_url=TAMU_API_BASE,
    )


def get_async_client(api_key: Optional[str] = None):
    """Nonblocking client for ASGI chat streaming."""
    return AsyncOpenAI(
        api_key=resolve_api_key(api_key),
        base_url=TAMU_API_BASE,
    )

async def _stream_messages(messages, model, api_key):
    """Close the asynchronous HTTP client and stream even on cancellation."""
    async with get_async_client(api_key=api_key) as client:
        stream = await client.chat.completions.create(
            model=model or TAMU_DEFAULT_MODEL,
            max_tokens=2048,
            messages=messages,
            stream=True,
            temperature=1,
        )
        async with stream:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content



async def fetch_tamu_models(api_key: Optional[str] = None) -> List[Dict[str, str]]:
    """Fetch and normalize model list from TAMU OpenAI-compatible endpoint."""
    headers = {"Authorization": f"Bearer {resolve_api_key(api_key)}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(TAMU_MODELS_URL, headers=headers)
        response.raise_for_status()
        payload = response.json()

    models_data = payload.get("data", []) if isinstance(payload, dict) else []
    normalized_models = []
    seen_ids = set()

    for model in models_data:
        if not isinstance(model, dict):
            continue

        openai_model = model.get("openai", {})
        if not isinstance(openai_model, dict):
            openai_model = {}

        model_id = model.get("id") or openai_model.get("id")
        if not model_id or model_id in seen_ids:
            continue

        model_name = model.get("name") or openai_model.get("name") or model_id
        normalized_models.append({"id": model_id, "name": model_name})
        seen_ids.add(model_id)

    normalized_models.sort(key=lambda m: m["name"].lower())

    if not normalized_models and TAMU_DEFAULT_MODEL:
        normalized_models.append({
            "id": TAMU_DEFAULT_MODEL,
            "name": TAMU_DEFAULT_MODEL,
        })

    return normalized_models


def encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """Encode image to base64 and determine media type."""
    path = Path(image_path)
    suffix = path.suffix.lower()

    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }

    if suffix not in media_type_map:
        raise ValueError(f"Unsupported image format: {suffix}; select PNG, JPEG, GIF, or WebP")
    media_type = media_type_map[suffix]

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    return image_data, media_type


def read_file_content(file_path: str) -> str:
    """Read complete source; missing or empty input is not valid chat context."""
    content = Path(file_path).read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"Selected source is empty: {file_path}")
    return content


def snapshot_files(analysis, repo_path: str):
    """Legacy runs cannot safely reconstruct their historical selection."""
    snapshot = analysis.selected_files
    if not isinstance(snapshot, list) or not snapshot:
        raise ValueError("This analysis has no saved input snapshot. Run a new analysis before chatting.")
    root = Path(repo_path).resolve()
    total = 0
    files = []
    for entry in snapshot:
        if not isinstance(entry, dict) or not isinstance(entry.get("file_path"), str):
            raise ValueError("Analysis input snapshot is invalid; run a new analysis.")
        path = (root / entry["file_path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Selected source is unavailable: {entry['file_path']}")
        total += path.stat().st_size
        files.append(SimpleNamespace(**entry))
    if total > MAX_ANALYSIS_SOURCE_BYTES:
        raise ValueError(f"Selected sources exceed chat's {MAX_ANALYSIS_SOURCE_BYTES}-byte context limit; run a new analysis with a smaller selection.")
    return files


async def build_erd_context(
    analysis: ERDAnalysis,
    repository: Repository,
    db: AsyncSession
) -> tuple[str, List[Dict]]:
    """
    Build context for ERD analysis chat.

    Returns:
        Tuple of (system_prompt, image_content_blocks)
    """
    repo_path = repository.local_path

    files = snapshot_files(analysis, repo_path)
    erd_files = [f for f in files if f.file_type == FileType.erd_image.value]
    story_files = [f for f in files if f.file_type != FileType.erd_image.value]

    # Build user stories content
    user_stories_content = ""
    for f in story_files:
        full_path = Path(repo_path) / f.file_path
        content = read_file_content(str(full_path))
        user_stories_content += f"\n\n### {f.file_path}\n{content}"

    # Parse analysis results
    uml_structure = json.loads(analysis.uml_structure) if analysis.uml_structure else {}
    report = json.loads(analysis.report) if analysis.report else {}

    # Build system prompt
    system_prompt = f"""You are an expert software architect helping the user understand an ERD (Entity-Relationship Diagram) analysis.

## Analysis Context

### Repository: {repository.name}

### UML Structure Extracted from ERD:
```json
{json.dumps(uml_structure, indent=2)}
```

### Analysis Report:
- Coverage Score: {report.get('coverage_score', 'N/A')}%
- Summary: {report.get('summary', 'N/A')}

### Missing Entities:
{json.dumps(report.get('missing_entities', []), indent=2)}

### Missing Relationships:
{json.dumps(report.get('missing_relationships', []), indent=2)}

### Cardinality Issues:
{json.dumps(report.get('cardinality_issues', []), indent=2)}

### Missing Attributes:
{json.dumps(report.get('missing_attributes', []), indent=2)}

### Data Integrity Concerns:
{json.dumps(report.get('data_integrity_concerns', []), indent=2)}

### User Story Coverage:
{json.dumps(report.get('user_story_coverage', []), indent=2)}

### Recommendations:
{json.dumps(report.get('recommendations', []), indent=2)}

### User Stories:
{user_stories_content}

## Instructions
- Answer questions about this ERD analysis clearly and helpfully
- Reference specific entities, relationships, and findings from the analysis
- When asked about improvements, provide concrete, actionable suggestions
- You can see the ERD images that were analyzed - reference visual elements when relevant
- Keep responses concise but thorough

{MARKDOWN_OUTPUT_POLICY}
"""

    # Build image content blocks for the ERD images (OpenAI vision format)
    image_blocks = []
    for f in erd_files:
        full_path = Path(repo_path) / f.file_path
        image_data, media_type = encode_image_to_base64(str(full_path))
        image_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{image_data}"},
        })

    return system_prompt, image_blocks


async def build_integrity_context(
    analysis: IntegrityAnalysis,
    repository: Repository,
    db: AsyncSession
) -> str:
    """
    Build context for Integrity analysis chat.

    Returns:
        System prompt string
    """
    repo_path = repository.local_path

    files = snapshot_files(analysis, repo_path)
    code_context = _build_code_context(files, repo_path)

    # Parse characteristic reports
    def parse_report(report_json):
        if not report_json:
            return {}
        try:
            return json.loads(report_json)
        except:
            return {}

    confidentiality = parse_report(analysis.confidentiality_report)
    data_integrity = parse_report(analysis.data_integrity_report)
    authenticity = parse_report(analysis.authenticity_report)
    non_repudiation = parse_report(analysis.non_repudiation_report)
    accountability = parse_report(analysis.accountability_report)
    resistance = parse_report(analysis.resistance_report)
    summary = parse_report(analysis.summary_report)

    system_prompt = f"""You are an expert security analyst helping the user understand an integrity/security analysis of their codebase.

## Analysis Context

### Repository: {repository.name}
### Overall Score: {analysis.overall_score}/100
### Risk Level: {summary.get('risk_level', 'N/A')}

### Executive Summary:
{summary.get('executive_summary', 'N/A')}

### Strengths:
{json.dumps(summary.get('strengths', []), indent=2)}

### Areas for Improvement:
{json.dumps(summary.get('areas_for_improvement', []), indent=2)}

### Priority Recommendations:
{json.dumps(summary.get('priority_recommendations', []), indent=2)}

---

## Characteristic Reports

### 1. Confidentiality (Score: {confidentiality.get('score', 'N/A')})
Status: {confidentiality.get('status', 'N/A')}
Description: {confidentiality.get('description', 'N/A')}
Findings: {json.dumps(confidentiality.get('findings', []), indent=2)}
Recommendations: {json.dumps(confidentiality.get('recommendations', []), indent=2)}

### 2. Data Integrity (Score: {data_integrity.get('score', 'N/A')})
Status: {data_integrity.get('status', 'N/A')}
Description: {data_integrity.get('description', 'N/A')}
Findings: {json.dumps(data_integrity.get('findings', []), indent=2)}
Recommendations: {json.dumps(data_integrity.get('recommendations', []), indent=2)}

### 3. Authenticity (Score: {authenticity.get('score', 'N/A')})
Status: {authenticity.get('status', 'N/A')}
Description: {authenticity.get('description', 'N/A')}
Findings: {json.dumps(authenticity.get('findings', []), indent=2)}
Recommendations: {json.dumps(authenticity.get('recommendations', []), indent=2)}

### 4. Non-Repudiation (Score: {non_repudiation.get('score', 'N/A')})
Status: {non_repudiation.get('status', 'N/A')}
Description: {non_repudiation.get('description', 'N/A')}
Findings: {json.dumps(non_repudiation.get('findings', []), indent=2)}
Recommendations: {json.dumps(non_repudiation.get('recommendations', []), indent=2)}

### 5. Accountability (Score: {accountability.get('score', 'N/A')})
Status: {accountability.get('status', 'N/A')}
Description: {accountability.get('description', 'N/A')}
Findings: {json.dumps(accountability.get('findings', []), indent=2)}
Recommendations: {json.dumps(accountability.get('recommendations', []), indent=2)}

### 6. Resistance (Score: {resistance.get('score', 'N/A')})
Status: {resistance.get('status', 'N/A')}
Description: {resistance.get('description', 'N/A')}
Findings: {json.dumps(resistance.get('findings', []), indent=2)}
Recommendations: {json.dumps(resistance.get('recommendations', []), indent=2)}

---

## Analyzed Code Files (for reference):
{code_context}

## Instructions
- Answer questions about this security/integrity analysis clearly and helpfully
- Reference specific findings, scores, and code snippets when relevant
- When asked about fixes, provide concrete code examples when possible
- Prioritize the most critical security concerns in your responses
- Keep responses concise but thorough

{MARKDOWN_OUTPUT_POLICY}
"""

    return system_prompt


async def stream_erd_chat(
    analysis_id: int,
    message: str,
    history: List[Dict[str, str]],
    db: AsyncSession,
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response about an ERD analysis.

    Yields chunks of the response text.
    """
    # Get analysis and repository
    result = await db.execute(
        select(ERDAnalysis).where(ERDAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise ValueError("Analysis not found")

    result = await db.execute(
        select(Repository).where(Repository.id == analysis.repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise ValueError("Repository not found")

    # Build context
    system_prompt, image_blocks = await build_erd_context(analysis, repository, db)

    # Build messages (OpenAI format - system message in messages array)
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add history
    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Include the original diagram on each turn, not just the first request.
    if image_blocks:
        messages.append({
            "role": "user",
            "content": [
                *image_blocks,
                {"type": "text", "text": message}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": message
        })

    async for chunk in _stream_messages(messages, model, api_key):
        yield chunk


def _parse_report(report_json):
    """Parse a JSON report string, returning {} on failure."""
    if not report_json:
        return {}
    try:
        return json.loads(report_json)
    except Exception:
        return {}


def _build_code_context(files, repo_path: str) -> str:
    """Include every snapshotted source without silent truncation."""
    code_files_summary = []
    for f in files:
        full_path = Path(repo_path) / f.file_path
        content = read_file_content(str(full_path))
        code_files_summary.append(f"### {f.file_path}\n```\n{content}\n```")
    return "\n\n".join(code_files_summary)


def _build_characteristics_section(reports: list) -> str:
    """Build characteristics section from list of (name, report_dict) tuples."""
    sections = []
    for i, (name, report) in enumerate(reports, 1):
        sections.append(f"""### {i}. {name} (Score: {report.get('score', 'N/A')})
Status: {report.get('status', 'N/A')}
Description: {report.get('description', 'N/A')}
Findings: {json.dumps(report.get('findings', []), indent=2)}
Recommendations: {json.dumps(report.get('recommendations', []), indent=2)}""")
    return "\n\n".join(sections)


async def _stream_analysis_chat(
    model_class,
    build_context_fn,
    analysis_id: int,
    message: str,
    history: List[Dict[str, str]],
    db: AsyncSession,
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Generic streaming chat for any analysis type."""
    result = await db.execute(
        select(model_class).where(model_class.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise ValueError("Analysis not found")

    result = await db.execute(
        select(Repository).where(Repository.id == analysis.repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise ValueError("Repository not found")

    system_prompt = await build_context_fn(analysis, repository, db)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    async for chunk in _stream_messages(messages, model, api_key):
        yield chunk


async def stream_integrity_chat(
    analysis_id: int,
    message: str,
    history: List[Dict[str, str]],
    db: AsyncSession,
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response about an integrity analysis.

    Yields chunks of the response text.
    """
    # Get analysis and repository
    result = await db.execute(
        select(IntegrityAnalysis).where(IntegrityAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise ValueError("Analysis not found")

    result = await db.execute(
        select(Repository).where(Repository.id == analysis.repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise ValueError("Repository not found")

    # Build context
    system_prompt = await build_integrity_context(analysis, repository, db)

    # Build messages (OpenAI format - system message in messages array)
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add history
    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add current message
    messages.append({
        "role": "user",
        "content": message
    })

    async for chunk in _stream_messages(messages, model, api_key):
        yield chunk


async def build_compliance_context(
    analysis: ComplianceAnalysis, repository: Repository, db: AsyncSession
) -> str:
    files = snapshot_files(analysis, repository.local_path)
    code_context = _build_code_context(files, repository.local_path)
    summary = _parse_report(analysis.summary_report)
    reports = [
        ("Functional Completeness", _parse_report(analysis.functional_completeness_report)),
        ("Functional Correctness", _parse_report(analysis.functional_correctness_report)),
        ("Functional Appropriateness", _parse_report(analysis.functional_appropriateness_report)),
    ]
    return f"""You are an expert software quality analyst helping the user understand a compliance / functional suitability analysis.

## Analysis Context
### Repository: {repository.name}
### Overall Score: {analysis.overall_score}/100
### Risk Level: {summary.get('risk_level', 'N/A')}
### Executive Summary:
{summary.get('executive_summary', 'N/A')}
### Strengths:
{json.dumps(summary.get('strengths', []), indent=2)}
### Areas for Improvement:
{json.dumps(summary.get('areas_for_improvement', []), indent=2)}
### Priority Recommendations:
{json.dumps(summary.get('priority_recommendations', []), indent=2)}
---
## Characteristic Reports
{_build_characteristics_section(reports)}
---
## Analyzed Code Files:
{code_context}
## Instructions
- Answer questions about this compliance analysis clearly and helpfully
- Reference specific findings, scores, and code snippets when relevant
- Keep responses concise but thorough

{MARKDOWN_OUTPUT_POLICY}
"""


async def stream_compliance_chat(
    analysis_id: int, message: str, history: List[Dict[str, str]],
    db: AsyncSession, model: Optional[str] = None, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_analysis_chat(
        ComplianceAnalysis, build_compliance_context,
        analysis_id, message, history, db, model, api_key
    ):
        yield chunk


async def build_correctness_context(
    analysis: CorrectnessAnalysis, repository: Repository, db: AsyncSession
) -> str:
    files = snapshot_files(analysis, repository.local_path)
    code_context = _build_code_context(files, repository.local_path)
    summary = _parse_report(analysis.summary_report)
    reports = [
        ("Functional Completeness (Correctness)", _parse_report(analysis.functional_completeness_correctness_report)),
        ("Functional Correctness (Accuracy)", _parse_report(analysis.functional_correctness_accuracy_report)),
        ("Functional Appropriateness (Correctness)", _parse_report(analysis.functional_appropriateness_correctness_report)),
    ]
    return f"""You are an expert software quality analyst helping the user understand a correctness analysis.

## Analysis Context
### Repository: {repository.name}
### Overall Score: {analysis.overall_score}/100
### Risk Level: {summary.get('risk_level', 'N/A')}
### Executive Summary:
{summary.get('executive_summary', 'N/A')}
### Strengths:
{json.dumps(summary.get('strengths', []), indent=2)}
### Areas for Improvement:
{json.dumps(summary.get('areas_for_improvement', []), indent=2)}
### Priority Recommendations:
{json.dumps(summary.get('priority_recommendations', []), indent=2)}
---
## Characteristic Reports
{_build_characteristics_section(reports)}
---
## Analyzed Code Files:
{code_context}
## Instructions
- Answer questions about this correctness analysis clearly and helpfully
- Reference specific findings, scores, and code snippets when relevant
- Keep responses concise but thorough

{MARKDOWN_OUTPUT_POLICY}
"""


async def stream_correctness_chat(
    analysis_id: int, message: str, history: List[Dict[str, str]],
    db: AsyncSession, model: Optional[str] = None, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_analysis_chat(
        CorrectnessAnalysis, build_correctness_context,
        analysis_id, message, history, db, model, api_key
    ):
        yield chunk


async def build_usability_context(
    analysis: UsabilityAnalysis, repository: Repository, db: AsyncSession
) -> str:
    files = snapshot_files(analysis, repository.local_path)
    code_context = _build_code_context(files, repository.local_path)
    summary = _parse_report(analysis.summary_report)
    reports = [
        ("Appropriateness Recognizability", _parse_report(analysis.appropriateness_recognizability_report)),
        ("Learnability", _parse_report(analysis.learnability_report)),
        ("Operability", _parse_report(analysis.operability_report)),
        ("User Error Protection", _parse_report(analysis.user_error_protection_report)),
        ("User Engagement", _parse_report(analysis.user_engagement_report)),
        ("Self-Descriptiveness", _parse_report(analysis.self_descriptiveness_report)),
        ("Inclusivity", _parse_report(analysis.inclusivity_report)),
        ("User Assistance", _parse_report(analysis.user_assistance_report)),
    ]
    return f"""You are an expert UX/usability analyst helping the user understand a usability analysis.

## Analysis Context
### Repository: {repository.name}
### Overall Score: {analysis.overall_score}/100
### Risk Level: {summary.get('risk_level', 'N/A')}
### Executive Summary:
{summary.get('executive_summary', 'N/A')}
### Strengths:
{json.dumps(summary.get('strengths', []), indent=2)}
### Areas for Improvement:
{json.dumps(summary.get('areas_for_improvement', []), indent=2)}
### Priority Recommendations:
{json.dumps(summary.get('priority_recommendations', []), indent=2)}
---
## Characteristic Reports
{_build_characteristics_section(reports)}
---
## Analyzed Code Files:
{code_context}
## Instructions
- Answer questions about this usability analysis clearly and helpfully
- Reference specific findings, scores, and code snippets when relevant
- Keep responses concise but thorough

{MARKDOWN_OUTPUT_POLICY}
"""


async def stream_usability_chat(
    analysis_id: int, message: str, history: List[Dict[str, str]],
    db: AsyncSession, model: Optional[str] = None, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_analysis_chat(
        UsabilityAnalysis, build_usability_context,
        analysis_id, message, history, db, model, api_key
    ):
        yield chunk


async def build_maintainability_context(
    analysis: MaintainabilityAnalysis, repository: Repository, db: AsyncSession
) -> str:
    files = snapshot_files(analysis, repository.local_path)
    code_context = _build_code_context(files, repository.local_path)
    summary = _parse_report(analysis.summary_report)
    reports = [
        ("Modularity", _parse_report(analysis.modularity_report)),
        ("Reusability", _parse_report(analysis.reusability_report)),
        ("Analysability", _parse_report(analysis.analysability_report)),
        ("Modifiability", _parse_report(analysis.modifiability_report)),
        ("Testability", _parse_report(analysis.testability_report)),
    ]
    return f"""You are an expert software architect helping the user understand a maintainability analysis.

## Analysis Context
### Repository: {repository.name}
### Overall Score: {analysis.overall_score}/100
### Risk Level: {summary.get('risk_level', 'N/A')}
### Executive Summary:
{summary.get('executive_summary', 'N/A')}
### Strengths:
{json.dumps(summary.get('strengths', []), indent=2)}
### Areas for Improvement:
{json.dumps(summary.get('areas_for_improvement', []), indent=2)}
### Priority Recommendations:
{json.dumps(summary.get('priority_recommendations', []), indent=2)}
---
## Characteristic Reports
{_build_characteristics_section(reports)}
---
## Analyzed Code Files:
{code_context}
## Instructions
- Answer questions about this maintainability analysis clearly and helpfully
- Reference specific findings, scores, and code snippets when relevant
- Keep responses concise but thorough

{MARKDOWN_OUTPUT_POLICY}
"""


async def stream_maintainability_chat(
    analysis_id: int, message: str, history: List[Dict[str, str]],
    db: AsyncSession, model: Optional[str] = None, api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_analysis_chat(
        MaintainabilityAnalysis, build_maintainability_context,
        analysis_id, message, history, db, model, api_key
    ):
        yield chunk
