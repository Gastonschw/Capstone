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

IMPORTANT: If this image does not appear to be an ERD or database diagram (e.g. it is a screenshot, UI mockup, or unrelated image), return the JSON with an empty "classes" array and add a note explaining that the image does not appear to contain an ERD.

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


async def extract_uml_from_text(text_content: str, file_path: str, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract UML structure from a text file that may describe an ERD
    (e.g. markdown tables, SQL DDL, textual entity descriptions).
    """
    client = get_client(api_key=api_key)
    resolved_model = model or TAMU_DEFAULT_MODEL

    extraction_prompt = f"""Analyze the following text file and extract any Entity-Relationship Diagram (ERD) or database schema information from it.

The file may contain ERD descriptions in any format: markdown tables, SQL CREATE statements, plain-text entity lists, structured schema descriptions, etc.

## File: {file_path}
```
{text_content[:8000]}
```

Return a JSON object with the same UML format:

{{
    "classes": [
        {{
            "name": "ClassName",
            "attributes": [
                {{
                    "name": "attribute_name",
                    "type": "data_type",
                    "visibility": "public",
                    "is_primary_key": true/false,
                    "is_foreign_key": true/false,
                    "is_nullable": true/false,
                    "default_value": "optional default"
                }}
            ],
            "methods": []
        }}
    ],
    "associations": [
        {{
            "source": "SourceClass",
            "target": "TargetClass",
            "association_type": "association|aggregation|composition",
            "source_multiplicity": "1|0..1|*|1..*|0..*",
            "target_multiplicity": "1|0..1|*|1..*|0..*",
            "label": "optional relationship name",
            "source_role": "",
            "target_role": ""
        }}
    ],
    "generalizations": [],
    "notes": []
}}

IMPORTANT: If this file does not contain any ERD, database schema, or entity/relationship information, return the JSON with an empty "classes" array and add a note explaining that the file does not appear to describe a data model.

Only return the JSON object, no additional text."""

    def _call_completion():
        resp = client.chat.completions.create(
            model=resolved_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": extraction_prompt}],
            stream=True,
        )
        return _collect_stream(resp)

    try:
        response_text = await asyncio.to_thread(_call_completion)
    except Exception as e:
        logger.error("Text-based ERD extraction failed for %s: %s", file_path, e)
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
        repaired = _repair_truncated_json(response_text.strip())
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
        return {
            "classes": [],
            "associations": [],
            "generalizations": [],
            "notes": [f"Failed to parse ERD from text file: {file_path}"]
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
Analyze whether the data model properly supports all the user stories. Return a JSON report.

CRITICAL RULE: Every finding MUST reference the specific user stories that justify it. Use user story IDs (e.g. "US-1", "US-2.1") when the stories have explicit IDs. If the stories do not have IDs, use a short summary of the story instead (e.g. "User login story", "Shopping cart checkout"). If a finding cannot be traced back to at least one user story, do NOT include it. This applies to ALL sections below.

JSON format:

{{
    "summary": "Brief overall assessment of how well the ERD supports the user stories",
    "coverage_score": 0-100,
    "missing_entities": [
        {{
            "entity_name": "suggested entity/class name",
            "user_story_ids": ["US-1", "US-2"],
            "reason": "which user story requires this and why",
            "suggested_attributes": ["attr1: type", "attr2: type"]
        }}
    ],
    "missing_relationships": [
        {{
            "from_entity": "Entity1",
            "to_entity": "Entity2",
            "user_story_ids": ["US-1"],
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
            "user_story_ids": ["US-3"],
            "reason": "explanation based on user story"
        }}
    ],
    "orphaned_entities": [
        {{
            "entity_name": "name",
            "user_story_ids": ["US-4"],
            "reason": "why this entity appears unnecessary for the given user stories"
        }}
    ],
    "missing_attributes": [
        {{
            "entity_name": "Entity",
            "attribute_name": "missing_attribute",
            "attribute_type": "suggested type",
            "user_story_ids": ["US-2"],
            "reason": "which user story requires this"
        }}
    ],
    "data_integrity_concerns": [
        {{
            "concern": "description of the concern",
            "affected_entities": ["Entity1", "Entity2"],
            "user_story_ids": ["US-1", "US-5"],
            "recommendation": "how to address it"
        }}
    ],
    "recommendations": [
        "Specific actionable recommendation 1",
        "Specific actionable recommendation 2"
    ],
    "user_story_coverage": [
        {{
            "story_id": "US-1",
            "story_summary": "brief summary of user story",
            "coverage_status": "fully_covered|partially_covered|not_covered",
            "notes": "explanation"
        }}
    ]
}}

Be thorough but fair. Only flag genuine issues that would prevent the user stories from being properly implemented. Remember: every finding must reference the user stories that justify it — by ID when available, by summary otherwise.

IMPORTANT: If after thorough examination the provided files do not appear to contain valid ERD diagrams or user stories (e.g. they are unrelated screenshots, code files, or generic documentation), note this clearly in the summary. Explain what you expected to find vs. what was actually provided, and suggest the user verify they selected the correct files. Still produce the best analysis you can with whatever content is available.

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

        selected = [f for f in files if f.is_selected_erd]

        if not selected:
            return WorkflowResult(
                success=False,
                error="No files selected. Please select at least one file for ERD analysis."
            )

        # Split selected files by actual extension — let users select anything
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
        image_files = [f for f in selected if Path(f.file_path).suffix.lower() in image_exts]
        text_files = [f for f in selected if Path(f.file_path).suffix.lower() not in image_exts]

        # Extract UML from images (if any)
        uml_structure = {"classes": [], "associations": [], "generalizations": [], "notes": []}
        if image_files:
            erd_image_paths = [str(Path(repo_path) / f.file_path) for f in image_files]
            uml_structure = await extract_uml_from_multiple_images(
                erd_image_paths, api_key=api_key, model=model
            )

        # For text files: try to extract ERD structure first, then treat
        # the rest as user stories.  This lets markdown/text ERDs work.
        story_paths = []
        if text_files:
            for tf in text_files:
                full_path = Path(repo_path) / tf.file_path
                try:
                    content = full_path.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    content = ""

                if not content.strip():
                    continue

                # Only attempt text-based ERD extraction when we still have
                # no classes (from images or a prior text file).
                if not uml_structure.get("classes"):
                    text_uml = await extract_uml_from_text(
                        content, tf.file_path, api_key=api_key, model=model
                    )
                    if text_uml.get("classes"):
                        # Merge into uml_structure
                        existing = {c["name"] for c in uml_structure["classes"]}
                        for cls in text_uml.get("classes", []):
                            if cls["name"] not in existing:
                                uml_structure["classes"].append(cls)
                                existing.add(cls["name"])
                        uml_structure["associations"].extend(text_uml.get("associations", []))
                        uml_structure["generalizations"].extend(text_uml.get("generalizations", []))
                        uml_structure["notes"].extend(text_uml.get("notes", []))
                        continue  # used as ERD, skip user-story path

                # Otherwise treat as user story content
                story_paths.append(tf.file_path)

        user_stories = ""
        if story_paths:
            user_stories = read_user_stories_from_files(repo_path, story_paths)

        # If we got nothing useful from either path, let the user know
        if not uml_structure.get("classes") and not user_stories.strip():
            return WorkflowResult(
                success=False,
                error="Could not extract any ERD structure or user stories from the selected files. "
                      "Please verify that the selected files contain ERD diagrams or user story content."
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
