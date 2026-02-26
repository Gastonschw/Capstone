"""
Correctness Analysis Service (ISO 25010 Functional Correctness focus)

Multi-agent workflow:
1. 3 Characteristic Agents - Completeness, Accuracy, Appropriateness (correctness lens)
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
class CorrectnessAnalysisResult:
    """Complete correctness analysis result."""
    functional_completeness_correctness: CharacteristicReport
    functional_correctness_accuracy: CharacteristicReport
    functional_appropriateness_correctness: CharacteristicReport
    overall_score: float
    summary: Dict


async def analyze_functional_completeness_correctness(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze completeness from a correctness perspective - are all required computations present?"""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for FUNCTIONAL COMPLETENESS (Correctness Perspective) - whether all required computations and data transformations are fully implemented.

Look for:
1. Missing computation steps in algorithms
2. Incomplete data transformations or conversions
3. Unimplemented branches in conditional logic
4. Missing null/undefined checks before computations
5. Incomplete loop termination conditions
6. Missing aggregation or reduction operations

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for correctness>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Functional Completeness (Correctness)", result, response_text or "")

    return CharacteristicReport(
        characteristic="Functional Completeness (Correctness)",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_functional_correctness_accuracy(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze accuracy of computations and outputs."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for FUNCTIONAL CORRECTNESS (Accuracy) - whether computations produce accurate results.

Look for:
1. Off-by-one errors in loops and array indexing
2. Floating-point precision issues
3. Integer overflow/underflow risks
4. Incorrect comparison operators (< vs <=, == vs ===)
5. Race conditions affecting result accuracy
6. Incorrect sort/filter/map implementations
7. Date/time calculation errors

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for accuracy>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Functional Correctness (Accuracy)", result, response_text or "")

    return CharacteristicReport(
        characteristic="Functional Correctness (Accuracy)",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def analyze_functional_appropriateness_correctness(
    repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
) -> CharacteristicReport:
    """Analyze whether functions use correct approaches for their intended purpose."""
    file_contents = prepare_file_contents(repo_path, files)

    prompt = f"""Analyze the following codebase for FUNCTIONAL APPROPRIATENESS (Correctness Perspective) - whether functions use the correct algorithmic approaches for their intended purpose.

Look for:
1. Anti-patterns that produce technically-correct but inappropriate results
2. Wrong data structures for the use case (e.g., O(n) where O(1) is possible)
3. Incorrect API usage patterns
4. Misuse of language features (e.g., mutable defaults, wrong async patterns)
5. Inappropriate error handling strategies
6. Wrong architectural patterns for the problem domain

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for correctness>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
    result = parse_json_response(response_text)
    default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
    description = _description_from_result(result, default_desc)
    _log_incomplete_response("Functional Appropriateness (Correctness)", result, response_text or "")

    return CharacteristicReport(
        characteristic="Functional Appropriateness (Correctness)",
        score=result.get("score", 50),
        status=result.get("status", "partially_fulfilled"),
        description=description,
        findings=result.get("findings", []),
        recommendations=result.get("recommendations", [])
    )


async def generate_correctness_summary(
    reports: List[CharacteristicReport], api_key: Optional[str] = None, model: Optional[str] = None
) -> Dict:
    """Generate overall correctness summary."""
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

    prompt = f"""Based on the following correctness analysis results, generate an executive summary.

Analysis Results:
{json.dumps(reports_data, indent=2)}

Provide:
1. An overall correctness score (weighted average, with Accuracy weighted higher)
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


async def run_correctness_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> CorrectnessAnalysisResult:
    """Main orchestrator: Runs the complete correctness analysis workflow."""
    repo_path = repository.local_path

    result = await db.execute(
        select(DiscoveredFile).where(
            DiscoveredFile.repository_id == repository.id,
            DiscoveredFile.is_selected_correctness == True
        )
    )
    files = result.scalars().all()

    if not files:
        raise ValueError("No files selected for correctness analysis")

    file_list = [{'file_path': f.file_path, 'file_type': f.file_type} for f in files]

    completeness = await analyze_functional_completeness_correctness(repo_path, file_list, api_key, model)
    accuracy = await analyze_functional_correctness_accuracy(repo_path, file_list, api_key, model)
    appropriateness = await analyze_functional_appropriateness_correctness(repo_path, file_list, api_key, model)

    all_reports = [completeness, accuracy, appropriateness]
    summary = await generate_correctness_summary(all_reports, api_key, model)

    return CorrectnessAnalysisResult(
        functional_completeness_correctness=completeness,
        functional_correctness_accuracy=accuracy,
        functional_appropriateness_correctness=appropriateness,
        overall_score=summary.get('overall_score', 50),
        summary=summary
    )
