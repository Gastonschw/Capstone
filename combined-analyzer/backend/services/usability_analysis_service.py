"""
Usability Analysis Service (ISO 25010 Usability / Interaction Capability)

Single-prompt workflow:
1. One combined prompt evaluates all 8 characteristics + summary
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
class UsabilityAnalysisResult:
    """Complete usability analysis result."""
    appropriateness_recognizability: CharacteristicReport
    learnability: CharacteristicReport
    operability: CharacteristicReport
    user_error_protection: CharacteristicReport
    user_engagement: CharacteristicReport
    self_descriptiveness: CharacteristicReport
    inclusivity: CharacteristicReport
    user_assistance: CharacteristicReport
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


async def run_usability_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> UsabilityAnalysisResult:
    """Main orchestrator: Runs the complete usability analysis in a single prompt."""
    repo_path = repository.local_path

    result = await db.execute(
        select(DiscoveredFile).where(
            DiscoveredFile.repository_id == repository.id,
            DiscoveredFile.is_selected_usability == True
        )
    )
    files = result.scalars().all()

    if not files:
        raise ValueError("No files selected for usability analysis")

    file_list = [{'file_path': f.file_path, 'file_type': f.file_type} for f in files]
    file_contents = prepare_file_contents(repo_path, file_list)

    prompt = f"""Analyze the following codebase for ISO 25010 USABILITY / INTERACTION CAPABILITY. Evaluate ALL EIGHT characteristics below in a single response.

## Characteristic 1: APPROPRIATENESS RECOGNIZABILITY
Whether users can recognize if the software is appropriate for their needs.
Look for:
1. Clear naming conventions that reveal purpose
2. Descriptive README, landing pages, or onboarding
3. Self-explanatory UI component names
4. Clear API endpoint naming and documentation
5. Meaningful error messages that guide users
6. Feature discoverability patterns

## Characteristic 2: LEARNABILITY
Whether users can easily learn to use the software.
Look for:
1. Consistent patterns across the codebase
2. Progressive disclosure of complexity
3. Tutorial or onboarding flows in the code
4. Documentation quality and completeness
5. Consistent API patterns
6. Example usage or demo data

## Characteristic 3: OPERABILITY
Whether the software is easy to operate and control.
Look for:
1. Keyboard navigation support
2. Form usability (clear labels, validation feedback)
3. Loading states and progress indicators
4. Undo/redo capabilities
5. Responsive design implementation
6. Configuration and customization options

## Characteristic 4: USER ERROR PROTECTION
Whether the system protects users from making errors.
Look for:
1. Input validation with helpful error messages
2. Confirmation dialogs for destructive actions
3. Type checking and constraints
4. Default values that prevent errors
5. Autosave or draft functionality
6. Clear warning messages before irreversible actions

## Characteristic 5: USER ENGAGEMENT
Whether the interface is engaging and satisfying to use.
Look for:
1. Visual feedback for user actions
2. Smooth animations and transitions
3. Consistent and appealing styling
4. Interactive elements and hover states
5. Success/completion feedback
6. Personalization features

## Characteristic 6: SELF-DESCRIPTIVENESS
Whether the software provides sufficient information for users to understand its behavior.
Look for:
1. Tooltips and help text in UI components
2. Inline documentation and comments
3. Status indicators and system state visibility
4. Clear labels and placeholder text
5. Contextual help and guidance
6. API response messages clarity

## Characteristic 7: INCLUSIVITY
Whether the software can be used by people with the widest range of characteristics.
Look for:
1. Accessibility attributes (ARIA labels, roles)
2. Color contrast compliance
3. Screen reader compatibility
4. Keyboard-only navigation support
5. Internationalization (i18n) support
6. Alternative text for images and media

## Characteristic 8: USER ASSISTANCE
Whether the software provides appropriate help and support.
Look for:
1. Help documentation or help pages
2. Contextual help (tooltips, info buttons)
3. Error recovery guidance
4. FAQ or troubleshooting content
5. Contact/support mechanisms
6. Search functionality for help content

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a single JSON object containing all eight characteristic evaluations plus an overall summary. Weight Operability and User Error Protection higher in the overall score:
{{
    "appropriateness_recognizability": {{
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
    "learnability": {{ ... same structure ... }},
    "operability": {{ ... same structure ... }},
    "user_error_protection": {{ ... same structure ... }},
    "user_engagement": {{ ... same structure ... }},
    "self_descriptiveness": {{ ... same structure ... }},
    "inclusivity": {{ ... same structure ... }},
    "user_assistance": {{ ... same structure ... }},
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
        logger.warning("Usability analysis returned no parseable result. Raw (first 800): %s", (response_text or "")[:800])

    appropriateness_recognizability = _extract_characteristic(result, "appropriateness_recognizability", "Appropriateness Recognizability")
    learnability = _extract_characteristic(result, "learnability", "Learnability")
    operability = _extract_characteristic(result, "operability", "Operability")
    user_error_protection = _extract_characteristic(result, "user_error_protection", "User Error Protection")
    user_engagement = _extract_characteristic(result, "user_engagement", "User Engagement")
    self_descriptiveness = _extract_characteristic(result, "self_descriptiveness", "Self-Descriptiveness")
    inclusivity = _extract_characteristic(result, "inclusivity", "Inclusivity")
    user_assistance = _extract_characteristic(result, "user_assistance", "User Assistance")

    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return UsabilityAnalysisResult(
        appropriateness_recognizability=appropriateness_recognizability,
        learnability=learnability,
        operability=operability,
        user_error_protection=user_error_protection,
        user_engagement=user_engagement,
        self_descriptiveness=self_descriptiveness,
        inclusivity=inclusivity,
        user_assistance=user_assistance,
        overall_score=summary.get('overall_score', 50),
        summary=summary,
    )
