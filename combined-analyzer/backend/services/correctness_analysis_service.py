"""
Correctness Analysis Service (ISO 25010 Functional Correctness focus)

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
    load_user_stories_for_repo,
    build_user_stories_prompt_section,
)


@dataclass
class CorrectnessAnalysisResult:
    """Complete correctness analysis result."""
    functional_completeness_correctness: CharacteristicReport
    functional_correctness_accuracy: CharacteristicReport
    functional_appropriateness_correctness: CharacteristicReport
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


async def run_correctness_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> CorrectnessAnalysisResult:
    """Main orchestrator: Runs the complete correctness analysis in a single prompt."""
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
    file_contents = prepare_file_contents(repo_path, file_list)

    # Load user stories for the completeness characteristic
    user_stories = await load_user_stories_for_repo(repo_path, repository.id, db)
    stories_section = build_user_stories_prompt_section(user_stories)

    prompt = f"""Analyze the following codebase for ISO 25010 FUNCTIONAL CORRECTNESS. Evaluate ALL THREE characteristics below in a single response.

## Characteristic 1: FUNCTIONAL COMPLETENESS (Correctness Perspective)
Whether all required computations and data transformations are fully implemented.
Look for:
1. Missing computation steps in algorithms
2. Incomplete data transformations or conversions
3. Unimplemented branches in conditional logic
4. Missing null/undefined checks before computations
5. Incomplete loop termination conditions
6. Missing aggregation or reduction operations
{stories_section}
## Characteristic 2: FUNCTIONAL CORRECTNESS (Accuracy)
Whether computations produce accurate results.
Look for:
1. Off-by-one errors in loops and array indexing
2. Floating-point precision issues
3. Integer overflow/underflow risks
4. Incorrect comparison operators (< vs <=, == vs ===)
5. Race conditions affecting result accuracy
6. Incorrect sort/filter/map implementations
7. Date/time calculation errors

## Characteristic 3: FUNCTIONAL APPROPRIATENESS (Correctness Perspective)
Whether functions use the correct algorithmic approaches for their intended purpose.
Look for:
1. Anti-patterns that produce technically-correct but inappropriate results
2. Wrong data structures for the use case (e.g., O(n) where O(1) is possible)
3. Incorrect API usage patterns
4. Misuse of language features (e.g., mutable defaults, wrong async patterns)
5. Inappropriate error handling strategies
6. Wrong architectural patterns for the problem domain

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a single JSON object containing all three characteristic evaluations plus an overall summary:
{{
    "functional_completeness_correctness": {{
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
    "functional_correctness_accuracy": {{
        "score": <0-100>,
        "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
        "description": "<2-3 sentence summary>",
        "findings": [...],
        "recommendations": [...]
    }},
    "functional_appropriateness_correctness": {{
        "score": <0-100>,
        "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
        "description": "<2-3 sentence summary>",
        "findings": [...],
        "recommendations": [...]
    }},
    "summary": {{
        "overall_score": <0-100 weighted average, with Accuracy weighted higher>,
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
        logger.warning("Correctness analysis returned no parseable result. Raw (first 800): %s", (response_text or "")[:800])

    completeness = _extract_characteristic(result, "functional_completeness_correctness", "Functional Completeness (Correctness)")
    accuracy = _extract_characteristic(result, "functional_correctness_accuracy", "Functional Correctness (Accuracy)")
    appropriateness = _extract_characteristic(result, "functional_appropriateness_correctness", "Functional Appropriateness (Correctness)")

    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return CorrectnessAnalysisResult(
        functional_completeness_correctness=completeness,
        functional_correctness_accuracy=accuracy,
        functional_appropriateness_correctness=appropriateness,
        overall_score=summary.get('overall_score', 50),
        summary=summary,
    )
