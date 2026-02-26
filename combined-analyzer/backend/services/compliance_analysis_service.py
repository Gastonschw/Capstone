"""
Compliance Analysis Service (ISO 25010 Functional Suitability)

Multi-agent workflow:
1. 3 Characteristic Agents - Functional Completeness, Correctness, Appropriateness
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
class ComplianceAnalysisResult:
    """Complete compliance analysis result."""
    functional_completeness: CharacteristicReport
    functional_correctness: CharacteristicReport
    functional_appropriateness: CharacteristicReport
    overall_score: float
    summary: Dict


async def analyze_functional_completeness(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze whether all specified functions are implemented."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for FUNCTIONAL COMPLETENESS - whether all specified or implied functions have been implemented.

Look for:
1. Feature coverage - are all expected features present based on code structure?
2. API endpoint completeness - do controllers/routes cover all CRUD operations?
3. Edge case handling - are boundary conditions addressed?
4. Error handling completeness - are all error paths covered?
5. Validation completeness - are all inputs validated?
6. Missing functionality gaps evident from code patterns

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of functional completeness>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for functional completeness>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Functional Completeness", result, response_text or "")

    return CharacteristicReport(
        characteristic="Functional Completeness",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_functional_correctness(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze whether functions provide correct results."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for FUNCTIONAL CORRECTNESS - whether the implemented functions provide correct results with the needed degree of precision.

Look for:
1. Algorithm correctness - are algorithms implemented correctly?
2. Data type handling - are types used correctly (precision, overflow)?
3. Business logic accuracy - does code correctly implement business rules?
4. Mathematical precision - are floating-point and rounding issues handled?
5. State management correctness - is state updated consistently?
6. Return value correctness - do functions return expected values?

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of functional correctness>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for functional correctness>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Functional Correctness", result, response_text or "")

    return CharacteristicReport(
        characteristic="Functional Correctness",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_functional_appropriateness(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze whether functions facilitate the accomplishment of specified tasks."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for FUNCTIONAL APPROPRIATENESS - whether the functions facilitate the accomplishment of specified tasks and objectives.

Look for:
1. API design appropriateness - are endpoints logical and well-organized?
2. Unnecessary complexity - are there over-engineered solutions?
3. Feature relevance - do implemented features serve actual user needs?
4. Workflow efficiency - do functions support efficient task completion?
5. Abstraction level - are abstractions at the right level?
6. Helper/utility appropriateness - are helpers useful and well-placed?

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of functional appropriateness>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for functional appropriateness>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Functional Appropriateness", result, response_text or "")

    return CharacteristicReport(
        characteristic="Functional Appropriateness",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def generate_compliance_summary(
    reports: List[CharacteristicReport], api_key: Optional[str] = None, model: Optional[str] = None
) -> Dict:
    """Generate overall compliance summary."""
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

    prompt = f"""Based on the following functional suitability / compliance analysis results, generate an executive summary.

Analysis Results:
{json.dumps(reports_data, indent=2)}

Provide:
1. An overall compliance score (weighted average)
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


async def run_compliance_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> ComplianceAnalysisResult:
    """Main orchestrator: Runs the complete compliance analysis workflow."""
    repo_path = repository.local_path

    result = await db.execute(
        select(DiscoveredFile).where(
            DiscoveredFile.repository_id == repository.id,
            DiscoveredFile.is_selected_compliance == True
        )
    )
    files = result.scalars().all()

    if not files:
        raise ValueError("No files selected for compliance analysis")

    file_list = [{'file_path': f.file_path, 'file_type': f.file_type} for f in files]

    functional_completeness = await analyze_functional_completeness(repo_path, file_list, api_key, model)
    functional_correctness = await analyze_functional_correctness(repo_path, file_list, api_key, model)
    functional_appropriateness = await analyze_functional_appropriateness(repo_path, file_list, api_key, model)

    all_reports = [functional_completeness, functional_correctness, functional_appropriateness]
    summary = await generate_compliance_summary(all_reports, api_key, model)

    return ComplianceAnalysisResult(
        functional_completeness=functional_completeness,
        functional_correctness=functional_correctness,
        functional_appropriateness=functional_appropriateness,
        overall_score=summary.get('overall_score', 50),
        summary=summary
    )
