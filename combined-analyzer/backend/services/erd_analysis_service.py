"""
ERD Analysis Service

Multi-agent workflow for repository analysis:
1. ERD to UML Agent - converts ERD diagrams to structured UML
2. Analysis Agent - analyzes UML against user stories

Uses TAMU API (OpenAI-compatible) so the same API key as chat works.
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.repository import Repository, DiscoveredFile, FileType
from models.erd_analysis import ERDAnalysis
from services.chat_service import get_client, TAMU_DEFAULT_MODEL


def _collect_stream(stream) -> str:
    """Collect streamed chunks into a single string, handling both SSE strings and OpenAI objects."""
    if isinstance(stream, str):
        # TAMU API sometimes returns raw SSE text — parse each data: line as JSON
        parts = []
        for line in stream.split("\n"):
            line = line.strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
                choices = chunk.get("choices", [])
                if choices:
                    content = choices[0].get("delta", {}).get("content", "")
                    if content:
                        parts.append(content)
            except json.JSONDecodeError:
                continue
        return "".join(parts)

    # Standard OpenAI streaming response (iterable of chunks)
    parts = []
    for chunk in stream:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content:
                parts.append(delta.content)
    return "".join(parts)


def _repair_truncated_json(text: str) -> Optional[str]:
    """Attempt to repair JSON truncated by token limits by closing open brackets."""
    if not text:
        return None
    # Strip any trailing incomplete string value
    # Find last complete key-value or array element
    # Then close all open brackets/braces
    stack = []
    in_string = False
    escape = False
    last_valid = 0
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            stack.append(ch)
            last_valid = i
        elif ch == '}':
            if stack and stack[-1] == '{':
                stack.pop()
                last_valid = i
        elif ch == ']':
            if stack and stack[-1] == '[':
                stack.pop()
                last_valid = i

    if not stack:
        return None  # Already balanced or unfixable

    # Truncate to last complete value boundary
    # Find the last comma, closing bracket, or colon+value before end
    truncated = text.rstrip()
    # Remove any trailing incomplete string/value
    while truncated and truncated[-1] not in ('}', ']', '"', ',', 'e', 'l', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
        truncated = truncated[:-1]
    # Remove trailing comma
    if truncated.endswith(','):
        truncated = truncated[:-1]
    # If we're in the middle of a string value, close it
    # Count unescaped quotes
    quote_count = 0
    esc = False
    for ch in truncated:
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
            continue
        if ch == '"':
            quote_count += 1
    if quote_count % 2 != 0:
        truncated += '"'

    # Close remaining open brackets
    # Re-scan to get current stack state
    stack2 = []
    in_string2 = False
    escape2 = False
    for ch in truncated:
        if escape2:
            escape2 = False
            continue
        if ch == '\\' and in_string2:
            escape2 = True
            continue
        if ch == '"' and not escape2:
            in_string2 = not in_string2
            continue
        if in_string2:
            continue
        if ch in ('{', '['):
            stack2.append(ch)
        elif ch == '}' and stack2 and stack2[-1] == '{':
            stack2.pop()
        elif ch == ']' and stack2 and stack2[-1] == '[':
            stack2.pop()

    closers = {'[': ']', '{': '}'}
    for bracket in reversed(stack2):
        truncated += closers.get(bracket, '')

    return truncated


@dataclass
class WorkflowResult:
    """Result of the complete analysis workflow."""
    success: bool
    uml_structure: Dict[str, Any] = None
    report: Dict[str, Any] = None
    coverage_score: float = None
    error: str = None


# ============== ERD to UML Extraction ==============

def encode_image(image_path: str) -> Tuple[str, str]:
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

    media_type = media_type_map.get(suffix, "image/png")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    return image_data, media_type


async def extract_uml_from_erd(image_path: str, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract detailed UML structure from an ERD image.
    Uses TAMU API (OpenAI-compatible) with vision support.
    """
    client = get_client(api_key=api_key)
    resolved_model = model or TAMU_DEFAULT_MODEL
    image_data, media_type = encode_image(image_path)

    extraction_prompt = """Analyze this Entity-Relationship Diagram (ERD) image and convert it to a detailed UML class diagram structure.

Return a JSON object with the following UML-oriented format:

{
    "classes": [
        {
            "name": "ClassName",
            "attributes": [
                {
                    "name": "attribute_name",
                    "type": "data_type",
                    "visibility": "public|private|protected",
                    "is_primary_key": true/false,
                    "is_foreign_key": true/false,
                    "is_nullable": true/false,
                    "default_value": "optional default"
                }
            ],
            "methods": ["method1()", "method2()"]
        }
    ],
    "associations": [
        {
            "source": "SourceClass",
            "target": "TargetClass",
            "association_type": "association|aggregation|composition",
            "source_multiplicity": "1|0..1|*|1..*|0..*",
            "target_multiplicity": "1|0..1|*|1..*|0..*",
            "label": "optional relationship name",
            "source_role": "optional role name",
            "target_role": "optional role name"
        }
    ],
    "generalizations": [
        {
            "parent": "ParentClass",
            "child": "ChildClass"
        }
    ],
    "notes": [
        "Any important notes or constraints visible in the diagram"
    ]
}

Guidelines:
- Extract ALL entities/tables as classes
- Map database columns to attributes with proper types
- Identify primary keys (PK) and foreign keys (FK)
- Determine relationship types:
  - Use "composition" for strong ownership (filled diamond)
  - Use "aggregation" for weak ownership (hollow diamond)
  - Use "association" for regular relationships (line)
- Extract cardinality/multiplicity from crow's foot notation or numeric labels
- Note any inheritance/generalization relationships

Be thorough and extract ALL elements visible in the diagram.
Only return the JSON object, no additional text."""

    def _call_completion():
        resp = client.chat.completions.create(
            model=resolved_model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": extraction_prompt
                        }
                    ],
                }
            ],
            stream=True,
        )
        return _collect_stream(resp)

    try:
        response_text = await asyncio.to_thread(_call_completion)
    except Exception as e:
        logger.error("ERD UML extraction API call failed: %s", e, exc_info=True)
        response_text = ""


    if not isinstance(response_text, str):
        logger.warning("ERD UML extraction returned non-string: %s", type(response_text))
        response_text = ""

    logger.info("ERD UML extraction response length: %d", len(response_text))
    if not response_text.strip():
        logger.error("ERD UML extraction returned empty response - the model may not support vision/image input")

    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(response_text.strip())
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
        logger.error("ERD UML extraction JSON parse failed (len=%d). End: %.300s", len(response_text), response_text[-300:])
        return {
            "raw_extraction": response_text,
            "classes": [],
            "associations": [],
            "generalizations": [],
            "notes": ["Failed to parse structured output"]
        }


async def extract_uml_from_multiple_images(
    image_paths: List[str],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract and merge UML structures from multiple ERD images.
    """
    all_classes = []
    all_associations = []
    all_generalizations = []
    all_notes = []

    for image_path in image_paths:
        try:
            uml = await extract_uml_from_erd(image_path, api_key=api_key, model=model)

            # Merge results (avoiding duplicates by class name)
            existing_class_names = {c["name"] for c in all_classes}
            for cls in uml.get("classes", []):
                if cls["name"] not in existing_class_names:
                    all_classes.append(cls)
                    existing_class_names.add(cls["name"])

            all_associations.extend(uml.get("associations", []))
            all_generalizations.extend(uml.get("generalizations", []))
            all_notes.extend(uml.get("notes", []))

        except Exception as e:
            all_notes.append(f"Error processing {image_path}: {str(e)}")

    # Deduplicate associations
    unique_associations = []
    seen = set()
    for assoc in all_associations:
        key = (assoc["source"], assoc["target"], assoc.get("label", ""))
        if key not in seen:
            unique_associations.append(assoc)
            seen.add(key)

    return {
        "classes": all_classes,
        "associations": unique_associations,
        "generalizations": all_generalizations,
        "notes": list(set(all_notes))
    }


# ============== Analysis Agent ==============

def read_user_stories_from_files(repo_path: str, story_files: List[str]) -> str:
    """
    Read and concatenate user stories from multiple files.
    """
    repo = Path(repo_path)
    all_stories = []

    for file_path in story_files:
        full_path = repo / file_path
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            all_stories.append(f"## From: {file_path}\n\n{content}")
        except Exception as e:
            all_stories.append(f"## From: {file_path}\n\n[Error reading file: {e}]")

    return "\n\n---\n\n".join(all_stories)


async def analyze_uml_against_stories(
    uml_structure: Dict[str, Any],
    user_stories: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze UML structure against user stories to find coverage issues.
    Uses TAMU API (OpenAI-compatible).
    """
    client = get_client(api_key=api_key)
    resolved_model = model or TAMU_DEFAULT_MODEL

    analysis_prompt = f"""You are an expert software architect and database analyst. Compare the following UML class diagram structure (derived from an ERD) against the user stories to identify mismatches and coverage issues.

## UML Structure (from ERD):
```json
{json.dumps(uml_structure, indent=2)}
```

## User Stories:
{user_stories}

## Your Task:
Analyze whether the data model properly supports all the user stories. Return a JSON report:

{{
    "summary": "Brief overall assessment of how well the ERD supports the user stories",
    "coverage_score": 0-100,
    "missing_entities": [
        {{
            "entity_name": "suggested entity/class name",
            "reason": "which user story requires this and why",
            "suggested_attributes": ["attr1: type", "attr2: type"]
        }}
    ],
    "missing_relationships": [
        {{
            "from_entity": "Entity1",
            "to_entity": "Entity2",
            "reason": "why this relationship is needed based on user stories",
            "suggested_type": "association|aggregation|composition",
            "suggested_multiplicity": "e.g., 1 to *"
        }}
    ],
    "cardinality_issues": [
        {{
            "relationship": "Entity1 -> Entity2",
            "current": "current multiplicity",
            "suggested": "correct multiplicity",
            "reason": "explanation based on user story"
        }}
    ],
    "orphaned_entities": [
        {{
            "entity_name": "name",
            "reason": "why this entity appears unnecessary for the given user stories"
        }}
    ],
    "missing_attributes": [
        {{
            "entity_name": "Entity",
            "attribute_name": "missing_attribute",
            "attribute_type": "suggested type",
            "reason": "which user story requires this"
        }}
    ],
    "data_integrity_concerns": [
        {{
            "concern": "description of the concern",
            "affected_entities": ["Entity1", "Entity2"],
            "recommendation": "how to address it"
        }}
    ],
    "recommendations": [
        "Specific actionable recommendation 1",
        "Specific actionable recommendation 2"
    ],
    "user_story_coverage": [
        {{
            "story_summary": "brief summary of user story",
            "coverage_status": "fully_covered|partially_covered|not_covered",
            "notes": "explanation"
        }}
    ]
}}

Be thorough but fair. Only flag genuine issues that would prevent the user stories from being properly implemented.
Only return the JSON object, no additional text."""

    def _call_completion():
        resp = client.chat.completions.create(
            model=resolved_model,
            max_tokens=16384,
            messages=[
                {"role": "user", "content": analysis_prompt}
            ],
            stream=True,
        )
        return _collect_stream(resp)

    try:
        response_text = await asyncio.to_thread(_call_completion)
    except Exception as e:
        logger.error("Analysis API call failed: %s", e, exc_info=True)
        response_text = ""
    if not isinstance(response_text, str):
        response_text = ""

    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Try to repair truncated JSON by closing open brackets/braces
        repaired = _repair_truncated_json(response_text.strip())
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
        logger.error("Analysis JSON parse failed (len=%d). End: %.300s", len(response_text), response_text[-300:])
        return {
            "summary": "Analysis completed but response parsing failed",
            "raw_analysis": response_text,
            "coverage_score": 0,
            "missing_entities": [],
            "missing_relationships": [],
            "cardinality_issues": [],
            "orphaned_entities": [],
            "missing_attributes": [],
            "data_integrity_concerns": [],
            "recommendations": [],
            "user_story_coverage": []
        }


# ============== Main Analysis Workflow ==============

async def run_erd_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> WorkflowResult:
    """
    Run the complete ERD analysis workflow on a repository.
    Uses TAMU API when api_key is provided (or from env).
    """
    repo_path = repository.local_path

    try:
        # Get selected files
        result = await db.execute(
            select(DiscoveredFile).where(
                DiscoveredFile.repository_id == repository.id
            )
        )
        files = result.scalars().all()

        erd_files = [f for f in files if f.file_type == FileType.erd_image.value and f.is_selected_erd]
        story_files = [f for f in files if f.file_type == FileType.user_story.value and f.is_selected_erd]

        # Validate we have required files
        if not erd_files:
            return WorkflowResult(
                success=False,
                error="No ERD images selected. Please select at least one ERD diagram image."
            )

        if not story_files:
            return WorkflowResult(
                success=False,
                error="No user story files selected. Please select at least one user story file."
            )

        # Extract UML from ERD images
        erd_image_paths = [
            str(Path(repo_path) / f.file_path)
            for f in erd_files
        ]

        uml_structure = await extract_uml_from_multiple_images(
            erd_image_paths, api_key=api_key, model=model
        )

        # Validate UML extraction
        if not uml_structure.get("classes"):
            return WorkflowResult(
                success=False,
                error="Failed to extract any entities from the ERD images. Please ensure the images contain valid ERD diagrams.",
                uml_structure=uml_structure
            )

        # Read user stories
        story_file_paths = [f.file_path for f in story_files]
        user_stories = read_user_stories_from_files(repo_path, story_file_paths)

        if not user_stories.strip():
            return WorkflowResult(
                success=False,
                error="User story files were found but appear to be empty.",
                uml_structure=uml_structure
            )

        # Run analysis
        report = await analyze_uml_against_stories(
            uml_structure, user_stories, api_key=api_key, model=model
        )
        coverage_score = report.get('coverage_score', 0)

        return WorkflowResult(
            success=True,
            uml_structure=uml_structure,
            report=report,
            coverage_score=coverage_score
        )

    except Exception as e:
        return WorkflowResult(
            success=False,
            error=f"Analysis workflow failed: {str(e)}"
        )
