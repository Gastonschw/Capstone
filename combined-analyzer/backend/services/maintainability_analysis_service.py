"""
Maintainability Analysis Service (ISO 25010 Maintainability)

Multi-agent workflow:
1. 5 Characteristic Agents - Modularity, Reusability, Analysability, Modifiability, Testability
2. Summary Agent - generate overall assessment

Uses TAMU API (OpenAI-compatible).
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.repository import Repository, DiscoveredFile
from services.integrity_analysis_service import (
    _tamu_completion,
    parse_json_response,
    prepare_file_contents,
    CharacteristicReport,
    _description_from_result,
    _log_incomplete_response,
)


@dataclass
class MaintainabilityAnalysisResult:
    """Complete maintainability analysis result."""
    modularity: CharacteristicReport
    reusability: CharacteristicReport
    analysability: CharacteristicReport
    modifiability: CharacteristicReport
    testability: CharacteristicReport
    overall_score: float
    summary: Dict


async def analyze_modularity(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze how well the system is composed of discrete, independent components."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for MODULARITY - how well the system is composed of discrete, independent components with minimal coupling.

Look for:
1. Separation of concerns (distinct modules/packages for different functionality)
2. Low coupling between modules (minimal cross-dependencies)
3. High cohesion within modules (related functionality grouped together)
4. Clear module boundaries and interfaces
5. Dependency injection patterns
6. Circular dependency issues

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of modularity>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for modularity>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Modularity", result, response_text or "")

    return CharacteristicReport(
        characteristic="Modularity",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_reusability(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze how well assets can be used in more than one system or context."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for REUSABILITY - how well code assets can be reused in more than one system, context, or module.

Look for:
1. Generic/reusable utility functions and helpers
2. Configurable components (not hard-coded values)
3. Well-defined interfaces and abstract base classes
4. DRY principle adherence (Don't Repeat Yourself)
5. Parameterized functions instead of duplicated logic
6. Shared component libraries

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of reusability>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for reusability>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Reusability", result, response_text or "")

    return CharacteristicReport(
        characteristic="Reusability",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_analysability(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze how easy it is to assess the impact of changes or diagnose defects."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for ANALYSABILITY - how easy it is to assess the impact of changes, diagnose defects, or identify parts that need modification.

Look for:
1. Code readability (clear naming, consistent style)
2. Documentation quality (comments, docstrings, READMEs)
3. Logging and tracing capabilities
4. Code complexity metrics (deeply nested logic, long functions)
5. Debugging support (meaningful error messages, stack traces)
6. Clear project structure and file organization

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of analysability>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for analysability>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Analysability", result, response_text or "")

    return CharacteristicReport(
        characteristic="Analysability",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_modifiability(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze how easily the software can be modified without introducing defects."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for MODIFIABILITY - how easily the software can be modified without introducing defects or degrading quality.

Look for:
1. Separation of configuration from code
2. Use of constants/enums instead of magic numbers
3. Extension points and plugin architectures
4. Avoidance of tight coupling and global state
5. Strategy/template patterns for varying behavior
6. Feature flags or toggles for gradual rollouts

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of modifiability>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for modifiability>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Modifiability", result, response_text or "")

    return CharacteristicReport(
        characteristic="Modifiability",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_testability(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze how effectively test criteria can be established and tests executed."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for TESTABILITY - how effectively test criteria can be established and tests executed to determine whether those criteria have been met.

Look for:
1. Existing test files and test coverage
2. Testable function design (pure functions, dependency injection)
3. Mock-friendly architecture (interfaces, abstractions)
4. Test configuration and fixtures
5. CI/CD test integration
6. Separation of side effects from business logic

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of testability>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for testability>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Testability", result, response_text or "")

    return CharacteristicReport(
        characteristic="Testability",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def generate_maintainability_summary(
    reports: List[CharacteristicReport], api_key: Optional[str] = None, model: Optional[str] = None
) -> Dict:
    """Generate overall maintainability summary."""
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

    prompt = f"""Based on the following maintainability analysis results, generate an executive summary.

Analysis Results:
{json.dumps(reports_data, indent=2)}

Provide:
1. An overall maintainability score (weighted average, with Modifiability and Testability weighted higher)
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
    return parse_json_response(response_text)


async def run_maintainability_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> MaintainabilityAnalysisResult:
    """Main orchestrator: Runs the complete maintainability analysis workflow."""
    repo_path = repository.local_path

    result = await db.execute(
        select(DiscoveredFile).where(
            DiscoveredFile.repository_id == repository.id,
            DiscoveredFile.is_selected_maintainability == True
        )
    )
    files = result.scalars().all()

    if not files:
        raise ValueError("No files selected for maintainability analysis")

    file_list = [{'file_path': f.file_path, 'file_type': f.file_type} for f in files]

    modularity = await analyze_modularity(repo_path, file_list, api_key, model)
    reusability = await analyze_reusability(repo_path, file_list, api_key, model)
    analysability = await analyze_analysability(repo_path, file_list, api_key, model)
    modifiability = await analyze_modifiability(repo_path, file_list, api_key, model)
    testability = await analyze_testability(repo_path, file_list, api_key, model)

    all_reports = [modularity, reusability, analysability, modifiability, testability]
    summary = await generate_maintainability_summary(all_reports, api_key, model)

    return MaintainabilityAnalysisResult(
        modularity=modularity,
        reusability=reusability,
        analysability=analysability,
        modifiability=modifiability,
        testability=testability,
        overall_score=summary.get('overall_score', 50),
        summary=summary
    )
