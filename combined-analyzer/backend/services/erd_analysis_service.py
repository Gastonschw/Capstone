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
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from services.chat_service import get_client, TAMU_DEFAULT_MODEL
from config import MAX_ANALYSIS_SOURCE_BYTES
from services.integrity_analysis_service import parse_json_response as parse_json_object


def _strings(value, field, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"Invalid or missing {field}")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"Invalid strings in {field}")


def _fields(value, fields):
    if not isinstance(value, dict):
        raise ValueError("Expected an object")
    for field in fields:
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"Invalid or missing {field}")


def _objects(value, field):
    items = value.get(field)
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise ValueError(f"Invalid or missing {field}")
    return items


def _validate_uml(value):
    for cls in _objects(value, "classes"):
        _fields(cls, ("name",))
        _strings(cls.get("methods"), "methods")
        for attr in _objects(cls, "attributes"):
            _fields(attr, ("name", "type", "visibility"))
            if attr["visibility"] not in {"public", "private", "protected"}:
                raise ValueError("Invalid attribute visibility")
            for field in ("is_primary_key", "is_foreign_key", "is_nullable"):
                if type(attr.get(field)) is not bool:
                    raise ValueError(f"Invalid or missing {field}")
            if "default_value" in attr and attr["default_value"] is not None and not isinstance(attr["default_value"], str):
                raise ValueError("Invalid attribute default_value")
    for assoc in _objects(value, "associations"):
        _fields(assoc, ("source", "target", "association_type", "source_multiplicity", "target_multiplicity"))
        if assoc["association_type"] not in {"association", "aggregation", "composition"}:
            raise ValueError("Invalid association type")
        for field in ("source_multiplicity", "target_multiplicity"):
            if assoc[field] not in {"1", "0..1", "*", "1..*", "0..*"}:
                raise ValueError("Invalid association multiplicity")
        for field in ("label", "source_role", "target_role"):
            if field in assoc and not isinstance(assoc[field], str):
                raise ValueError(f"Invalid {field}")
    for gen in _objects(value, "generalizations"):
        _fields(gen, ("parent", "child"))
    _strings(value.get("notes"), "notes")
    return value


def _validate_report(value):
    _fields(value, ("summary",))
    score = value.get("coverage_score")
    if type(score) not in (int, float) or not 0 <= score <= 100:
        raise ValueError("Invalid coverage_score")
    sections = {
        "missing_entities": ("entity_name", "reason"),
        "missing_relationships": ("from_entity", "to_entity", "reason", "suggested_type", "suggested_multiplicity"),
        "cardinality_issues": ("relationship", "current", "suggested", "reason"),
        "orphaned_entities": ("entity_name", "reason"),
        "missing_attributes": ("entity_name", "attribute_name", "attribute_type", "reason"),
        "data_integrity_concerns": ("concern", "recommendation"),
    }
    for section, fields in sections.items():
        for finding in _objects(value, section):
            _fields(finding, fields)
            _strings(finding.get("user_story_ids"), "user_story_ids", nonempty=True)
            if section == "missing_entities":
                _strings(finding.get("suggested_attributes"), "suggested_attributes")
            if section == "data_integrity_concerns":
                _strings(finding.get("affected_entities"), "affected_entities", nonempty=True)
            if section == "missing_relationships" and finding["suggested_type"] not in {"association", "aggregation", "composition"}:
                raise ValueError("Invalid suggested relationship type")
    _strings(value.get("recommendations"), "recommendations")
    coverage = _objects(value, "user_story_coverage")
    if not coverage:
        raise ValueError("Report must assess at least one user story")
    for story in coverage:
        _fields(story, ("story_id", "story_summary", "coverage_status", "notes"))
        if story["coverage_status"] not in {"fully_covered", "partially_covered", "not_covered"}:
            raise ValueError("Invalid story coverage status")
    return value


def _merge_uml(structures):
    merged = {"classes": [], "associations": [], "generalizations": [], "notes": []}
    classes = {}
    for structure in structures:
        for cls in structure["classes"]:
            if cls["name"] not in classes:
                classes[cls["name"]] = cls
                merged["classes"].append(cls)
                continue
            existing = classes[cls["name"]]
            attributes = {attr["name"]: attr for attr in existing["attributes"]}
            for attr in cls["attributes"]:
                if attr["name"] in attributes and attributes[attr["name"]] != attr:
                    raise ValueError(f"Conflicting schema attribute: {cls['name']}.{attr['name']}")
                if attr["name"] not in attributes:
                    existing["attributes"].append(attr)
                    attributes[attr["name"]] = attr
            existing["methods"].extend(method for method in cls["methods"] if method not in existing["methods"])
        for section in ("associations", "generalizations", "notes"):
            for item in structure[section]:
                if item not in merged[section]:
                    merged[section].append(item)
    return merged


def validate_selected_files(repo_path, selected_files):
    """Preflight the full snapshot before inserting a job or calling a provider."""
    if not selected_files:
        raise ValueError("No files selected for ERD analysis.")
    root = Path(repo_path).resolve()
    prepared = []
    total_bytes = 0
    for selected in selected_files:
        relative = selected["file_path"]
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Selected file is missing or outside the repository: {relative}")
        suffix = path.suffix.lower()
        if suffix in {".svg", ".bmp"}:
            raise ValueError(f"Unsupported ERD image format: {suffix}")
        if total_bytes + path.stat().st_size > MAX_ANALYSIS_SOURCE_BYTES:
            raise ValueError(f"Selected ERD inputs exceed the {MAX_ANALYSIS_SOURCE_BYTES}-byte capacity.")
        with path.open("rb") as source:
            data = source.read(MAX_ANALYSIS_SOURCE_BYTES - total_bytes + 1)
        total_bytes += len(data)
        if total_bytes > MAX_ANALYSIS_SOURCE_BYTES:
            raise ValueError(f"Selected ERD inputs exceed the {MAX_ANALYSIS_SOURCE_BYTES}-byte capacity.")
        if not data:
            raise ValueError(f"Selected file is empty: {relative}")
        image = suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        content = None if image else data.decode("utf-8")
        if content is not None and not content.strip():
            raise ValueError(f"Selected file is empty: {relative}")
        prepared.append({"path": relative, "absolute_path": str(path), "image": image, "content": content})
    return prepared


def _collect_stream(stream) -> str:
    """Reject malformed or incomplete provider streams rather than partial reports."""
    parts = []
    finished = False
    if isinstance(stream, str):
        for line in stream.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            if chunk.get("error"):
                raise ValueError("ERD provider returned an error")
            choices = chunk.get("choices", [])
            if not choices:
                continue
            choice = choices[0]
            reason = choice.get("finish_reason")
            if reason is not None:
                if reason != "stop":
                    raise ValueError(f"ERD provider response incomplete: {reason}")
                finished = True
            content = choice.get("delta", {}).get("content")
            if content:
                parts.append(content)
    else:
        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue
            choice = chunk.choices[0]
            reason = getattr(choice, "finish_reason", None)
            if reason is not None:
                if reason != "stop":
                    raise ValueError(f"ERD provider response incomplete: {reason}")
                finished = True
            content = getattr(choice.delta, "content", None)
            if content:
                parts.append(content)
    if not finished or not parts:
        raise ValueError("ERD provider returned an empty or incomplete response")
    return "".join(parts)




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

    if suffix not in media_type_map:
        raise ValueError(f"Unsupported ERD image format: {suffix}")
    media_type = media_type_map[suffix]

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

    response_text = await asyncio.to_thread(_call_completion)
    return _validate_uml(parse_json_object(response_text))


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
{text_content}
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

    response_text = await asyncio.to_thread(_call_completion)
    return _validate_uml(parse_json_object(response_text))




# ============== Analysis Agent ==============



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

IMPORTANT: If the selected content does not contain valid user stories, fail explicitly rather than inventing requirements or returning a successful empty assessment.

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

    response_text = await asyncio.to_thread(_call_completion)
    return _validate_report(parse_json_object(response_text))


# ============== Main Analysis Workflow ==============

async def run_erd_analysis(
    repository: Repository,
    db: AsyncSession,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    selected_files: Optional[List[Dict[str, Any]]] = None,
) -> WorkflowResult:
    """Analyze only the immutable selection captured when the job was created."""
    try:
        prepared = validate_selected_files(repository.local_path, selected_files)
        images = [item["absolute_path"] for item in prepared if item["image"]]
        texts = [(item["path"], item["content"]) for item in prepared if not item["image"]]
        structures = []
        for image in images:
            structures.append(await extract_uml_from_erd(image, api_key=api_key, model=model))
        stories = []
        for relative, content in texts:
            extracted = await extract_uml_from_text(content, relative, api_key=api_key, model=model)
            if extracted["classes"]:
                structures.append(extracted)
            else:
                stories.append(f"## From: {relative}\n\n{content}")
        uml_structure = _merge_uml(structures)
        if not uml_structure["classes"]:
            raise ValueError("Selected files do not contain an ERD schema.")
        if not stories:
            raise ValueError("Select user-story files in addition to ERD schema files.")
        report = await analyze_uml_against_stories(
            uml_structure, "\n\n---\n\n".join(stories), api_key=api_key, model=model
        )
        return WorkflowResult(
            success=True, uml_structure=uml_structure, report=report,
            coverage_score=report["coverage_score"],
        )
    except Exception as exc:
        return WorkflowResult(success=False, error=f"Analysis workflow failed: {exc}")
