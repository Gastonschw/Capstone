"""
Usability Analysis Service (ISO 25010 Usability / Interaction Capability)

Multi-agent workflow:
1. 8 Characteristic Agents
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


def _usability_agent(characteristic: str, description: str, look_for: str):
    """Factory for usability characteristic analysis functions."""
    async def analyze(
        repo_path: str, files: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None
    ) -> CharacteristicReport:
        file_contents = prepare_file_contents(repo_path, files)

        prompt = f"""Analyze the following codebase for {characteristic.upper()} - {description}

Look for:
{look_for}

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of {characteristic.lower()}>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for {characteristic.lower()}>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

        response_text = await asyncio.to_thread(_tamu_completion, api_key, prompt, 4096, model)
        result = parse_json_response(response_text)
        default_desc = "No structured result from model (check API key and response format)." if not result else "Analysis incomplete"
        desc = _description_from_result(result, default_desc)
        _log_incomplete_response(characteristic, result, response_text or "")

        return CharacteristicReport(
            characteristic=characteristic,
            score=result.get("score", 50),
            status=result.get("status", "partially_fulfilled"),
            description=desc,
            findings=result.get("findings", []),
            recommendations=result.get("recommendations", [])
        )

    return analyze


analyze_appropriateness_recognizability = _usability_agent(
    "Appropriateness Recognizability",
    "whether users can recognize if the software is appropriate for their needs.",
    """1. Clear naming conventions that reveal purpose
2. Descriptive README, landing pages, or onboarding
3. Self-explanatory UI component names
4. Clear API endpoint naming and documentation
5. Meaningful error messages that guide users
6. Feature discoverability patterns"""
)

analyze_learnability = _usability_agent(
    "Learnability",
    "whether users can easily learn to use the software.",
    """1. Consistent patterns across the codebase
2. Progressive disclosure of complexity
3. Tutorial or onboarding flows in the code
4. Documentation quality and completeness
5. Consistent API patterns
6. Example usage or demo data"""
)

analyze_operability = _usability_agent(
    "Operability",
    "whether the software is easy to operate and control.",
    """1. Keyboard navigation support
2. Form usability (clear labels, validation feedback)
3. Loading states and progress indicators
4. Undo/redo capabilities
5. Responsive design implementation
6. Configuration and customization options"""
)

analyze_user_error_protection = _usability_agent(
    "User Error Protection",
    "whether the system protects users from making errors.",
    """1. Input validation with helpful error messages
2. Confirmation dialogs for destructive actions
3. Type checking and constraints
4. Default values that prevent errors
5. Autosave or draft functionality
6. Clear warning messages before irreversible actions"""
)

analyze_user_engagement = _usability_agent(
    "User Engagement",
    "whether the interface is engaging and satisfying to use.",
    """1. Visual feedback for user actions
2. Smooth animations and transitions
3. Consistent and appealing styling
4. Interactive elements and hover states
5. Success/completion feedback
6. Personalization features"""
)

analyze_self_descriptiveness = _usability_agent(
    "Self-Descriptiveness",
    "whether the software provides sufficient information for users to understand its behavior.",
    """1. Tooltips and help text in UI components
2. Inline documentation and comments
3. Status indicators and system state visibility
4. Clear labels and placeholder text
5. Contextual help and guidance
6. API response messages clarity"""
)

analyze_inclusivity = _usability_agent(
    "Inclusivity",
    "whether the software can be used by people with the widest range of characteristics.",
    """1. Accessibility attributes (ARIA labels, roles)
2. Color contrast compliance
3. Screen reader compatibility
4. Keyboard-only navigation support
5. Internationalization (i18n) support
6. Alternative text for images and media"""
)

analyze_user_assistance = _usability_agent(
    "User Assistance",
    "whether the software provides appropriate help and support.",
    """1. Help documentation or help pages
2. Contextual help (tooltips, info buttons)
3. Error recovery guidance
4. FAQ or troubleshooting content
5. Contact/support mechanisms
6. Search functionality for help content"""
)


async def generate_usability_summary(
    reports: List[CharacteristicReport], api_key: Optional[str] = None, model: Optional[str] = None
) -> Dict:
    """Generate overall usability summary."""
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

    prompt = f"""Based on the following usability analysis results, generate an executive summary.

Analysis Results:
{json.dumps(reports_data, indent=2)}

Provide:
1. An overall usability score (weighted average, with Operability and User Error Protection weighted higher)
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


async def run_usability_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> UsabilityAnalysisResult:
    """Main orchestrator: Runs the complete usability analysis workflow."""
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

    appropriateness_recognizability = await analyze_appropriateness_recognizability(repo_path, file_list, api_key, model)
    learnability = await analyze_learnability(repo_path, file_list, api_key, model)
    operability = await analyze_operability(repo_path, file_list, api_key, model)
    user_error_protection = await analyze_user_error_protection(repo_path, file_list, api_key, model)
    user_engagement = await analyze_user_engagement(repo_path, file_list, api_key, model)
    self_descriptiveness = await analyze_self_descriptiveness(repo_path, file_list, api_key, model)
    inclusivity = await analyze_inclusivity(repo_path, file_list, api_key, model)
    user_assistance = await analyze_user_assistance(repo_path, file_list, api_key, model)

    all_reports = [
        appropriateness_recognizability, learnability, operability, user_error_protection,
        user_engagement, self_descriptiveness, inclusivity, user_assistance
    ]
    summary = await generate_usability_summary(all_reports, api_key, model)

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
        summary=summary
    )
