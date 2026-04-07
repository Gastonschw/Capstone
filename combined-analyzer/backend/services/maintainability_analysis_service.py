"""
Maintainability Analysis Service (ISO 25010 Maintainability)

Single-prompt workflow:
1. One combined prompt evaluates all 5 characteristics + summary
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


async def run_maintainability_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> MaintainabilityAnalysisResult:
    """Main orchestrator: Runs the complete maintainability analysis in a single prompt."""
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
    file_contents = prepare_file_contents(repo_path, file_list)

    prompt = f"""Analyze the following codebase for ISO 25010 MAINTAINABILITY. Evaluate ALL FIVE characteristics below in a single response.

## Characteristic 1: MODULARITY
How well the system is composed of discrete, independent components with minimal coupling.
Look for:
1. Separation of concerns (distinct modules/packages for different functionality)
2. Low coupling between modules (minimal cross-dependencies)
3. High cohesion within modules (related functionality grouped together)
4. Clear module boundaries and interfaces
5. Dependency injection patterns
6. Circular dependency issues

## Characteristic 2: REUSABILITY
How well code assets can be reused in more than one system, context, or module.
Look for:
1. Generic/reusable utility functions and helpers
2. Configurable components (not hard-coded values)
3. Well-defined interfaces and abstract base classes
4. DRY principle adherence (Don't Repeat Yourself)
5. Parameterized functions instead of duplicated logic
6. Shared component libraries

## Characteristic 3: ANALYSABILITY
How easy it is to assess the impact of changes, diagnose defects, or identify parts that need modification.
Look for:
1. Code readability (clear naming, consistent style)
2. Documentation quality (comments, docstrings, READMEs)
3. Logging and tracing capabilities
4. Code complexity metrics (deeply nested logic, long functions)
5. Debugging support (meaningful error messages, stack traces)
6. Clear project structure and file organization

## Characteristic 4: MODIFIABILITY
How easily the software can be modified without introducing defects or degrading quality.
Look for:
1. Separation of configuration from code
2. Use of constants/enums instead of magic numbers
3. Extension points and plugin architectures
4. Avoidance of tight coupling and global state
5. Strategy/template patterns for varying behavior
6. Feature flags or toggles for gradual rollouts

## Characteristic 5: TESTABILITY
How effectively test criteria can be established and tests executed to determine whether those criteria have been met.
Look for:
1. Existing test files and test coverage
2. Testable function design (pure functions, dependency injection)
3. Mock-friendly architecture (interfaces, abstractions)
4. Test configuration and fixtures
5. CI/CD test integration
6. Separation of side effects from business logic

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a single JSON object containing all five characteristic evaluations plus an overall summary. Weight Modifiability and Testability higher in the overall score:
{{
    "modularity": {{
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
    "reusability": {{ ... same structure ... }},
    "analysability": {{ ... same structure ... }},
    "modifiability": {{ ... same structure ... }},
    "testability": {{ ... same structure ... }},
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
        logger.warning("Maintainability analysis returned no parseable result. Raw (first 800): %s", (response_text or "")[:800])

    modularity = _extract_characteristic(result, "modularity", "Modularity")
    reusability = _extract_characteristic(result, "reusability", "Reusability")
    analysability = _extract_characteristic(result, "analysability", "Analysability")
    modifiability = _extract_characteristic(result, "modifiability", "Modifiability")
    testability = _extract_characteristic(result, "testability", "Testability")

    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return MaintainabilityAnalysisResult(
        modularity=modularity,
        reusability=reusability,
        analysability=analysability,
        modifiability=modifiability,
        testability=testability,
        overall_score=summary.get('overall_score', 50),
        summary=summary,
    )
