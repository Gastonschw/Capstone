"""
Compliance Analysis Service (ISO 25010 Functional Suitability)

Single-prompt workflow:
1. One combined prompt evaluates all 3 characteristics + summary
2. Response is split into individual CharacteristicReport objects

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
    load_user_stories_for_repo,
    build_user_stories_prompt_section,
)


@dataclass
class ComplianceAnalysisResult:
    """Complete compliance analysis result."""
    functional_completeness: CharacteristicReport
    functional_correctness: CharacteristicReport
    functional_appropriateness: CharacteristicReport
    overall_score: float
    summary: Dict


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


async def run_compliance_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> ComplianceAnalysisResult:
    """Main orchestrator: Runs the complete compliance analysis in a single prompt."""
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
    file_contents = prepare_file_contents(repo_path, file_list)

    # Load user stories for requirements-aware analysis
    user_stories = await load_user_stories_for_repo(repo_path, repository.id, db)
    stories_section = build_user_stories_prompt_section(user_stories)

    prompt = f"""Analyze the following codebase for ISO 25010 FUNCTIONAL SUITABILITY. Evaluate ALL THREE characteristics below in a single response.

## Characteristic 1: FUNCTIONAL COMPLETENESS
Whether all specified or implied functions have been implemented.
Look for:
1. Feature coverage - are all expected features present based on code structure?
2. API endpoint completeness - do controllers/routes cover all CRUD operations?
3. Edge case handling - are boundary conditions addressed?
4. Error handling completeness - are all error paths covered?
5. Validation completeness - are all inputs validated?
6. Missing functionality gaps evident from code patterns

## Characteristic 2: FUNCTIONAL CORRECTNESS
Whether the implemented functions provide correct results with the needed degree of precision.
Look for:
1. Algorithm correctness - are algorithms implemented correctly?
2. Data type handling - are types used correctly (precision, overflow)?
3. Business logic accuracy - does code correctly implement business rules?
4. Mathematical precision - are floating-point and rounding issues handled?
5. State management correctness - is state updated consistently?
6. Return value correctness - do functions return expected values?

## Characteristic 3: FUNCTIONAL APPROPRIATENESS
Whether the functions facilitate the accomplishment of specified tasks and objectives.
Look for:
1. API design appropriateness - are endpoints logical and well-organized?
2. Unnecessary complexity - are there over-engineered solutions?
3. Feature relevance - do implemented features serve actual user needs?
4. Workflow efficiency - do functions support efficient task completion?
5. Abstraction level - are abstractions at the right level?
6. Helper/utility appropriateness - are helpers useful and well-placed?
{stories_section}
Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a single JSON object containing all three characteristic evaluations plus an overall summary:
{{
    "functional_completeness": {{
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
    "functional_correctness": {{
        "score": <0-100>,
        "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
        "description": "<2-3 sentence summary>",
        "findings": [...],
        "recommendations": [...]
    }},
    "functional_appropriateness": {{
        "score": <0-100>,
        "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
        "description": "<2-3 sentence summary>",
        "findings": [...],
        "recommendations": [...]
    }},
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
        logger.warning("Compliance analysis returned no parseable result. Raw (first 800): %s", (response_text or "")[:800])

    functional_completeness = _extract_characteristic(result, "functional_completeness", "Functional Completeness")
    functional_correctness = _extract_characteristic(result, "functional_correctness", "Functional Correctness")
    functional_appropriateness = _extract_characteristic(result, "functional_appropriateness", "Functional Appropriateness")

    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return ComplianceAnalysisResult(
        functional_completeness=functional_completeness,
        functional_correctness=functional_correctness,
        functional_appropriateness=functional_appropriateness,
        overall_score=summary.get('overall_score', 50),
        summary=summary,
    )
