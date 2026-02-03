import anthropic
import base64
import json
import os
from pathlib import Path


def get_client():
    return anthropic.Anthropic()


def encode_image(image_path: str) -> tuple[str, str]:
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


def extract_erd_from_image(image_path: str) -> dict:
    """Step 1: Use Claude Vision to extract ERD structure from image."""
    client = get_client()
    image_data, media_type = encode_image(image_path)

    extraction_prompt = """Analyze this Entity-Relationship Diagram (ERD) image and extract its structure.

Return a JSON object with the following format:
{
    "entities": [
        {
            "name": "EntityName",
            "attributes": [
                {"name": "attribute_name", "type": "data_type", "is_primary_key": true/false, "is_foreign_key": true/false}
            ]
        }
    ],
    "relationships": [
        {
            "from_entity": "Entity1",
            "to_entity": "Entity2",
            "relationship_type": "one-to-many|many-to-many|one-to-one",
            "from_cardinality": "1|0..1|*|1..*|0..*",
            "to_cardinality": "1|0..1|*|1..*|0..*",
            "relationship_name": "optional relationship label if visible"
        }
    ]
}

Be thorough and extract ALL entities, attributes, and relationships visible in the diagram.
Only return the JSON object, no additional text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": extraction_prompt
                    }
                ],
            }
        ],
    )

    response_text = message.content[0].text

    # Try to parse JSON from response
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Return raw text if JSON parsing fails
        return {"raw_extraction": response_text, "entities": [], "relationships": []}


def analyze_erd_against_stories(extracted_erd: dict, user_stories: str) -> dict:
    """Step 2: Compare extracted ERD against user stories to find mismatches."""
    client = get_client()

    analysis_prompt = f"""You are an expert database analyst. Compare the following ERD (Entity-Relationship Diagram) structure against the user stories to identify mismatches and coverage issues.

## Extracted ERD Structure:
```json
{json.dumps(extracted_erd, indent=2)}
```

## User Stories:
{user_stories}

## Your Task:
Analyze whether the ERD properly supports all the user stories. Return a JSON report with the following structure:

{{
    "summary": "Brief overall assessment",
    "coverage_score": 0-100,
    "missing_entities": [
        {{
            "entity_name": "suggested entity name",
            "reason": "which user story requires this",
            "suggested_attributes": ["attr1", "attr2"]
        }}
    ],
    "missing_relationships": [
        {{
            "from_entity": "Entity1",
            "to_entity": "Entity2",
            "reason": "why this relationship is needed",
            "suggested_type": "one-to-many|many-to-many|one-to-one"
        }}
    ],
    "cardinality_issues": [
        {{
            "relationship": "Entity1 -> Entity2",
            "current": "current cardinality",
            "suggested": "correct cardinality",
            "reason": "explanation"
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
            "attribute_name": "missing attribute",
            "reason": "which user story requires this"
        }}
    ],
    "recommendations": [
        "Specific actionable recommendation 1",
        "Specific actionable recommendation 2"
    ]
}}

Be thorough but fair. Only flag genuine issues that would prevent the user stories from being implemented.
Only return the JSON object, no additional text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": analysis_prompt
            }
        ],
    )

    response_text = message.content[0].text

    # Try to parse JSON from response
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        return {
            "summary": "Analysis completed but response parsing failed",
            "raw_analysis": response_text,
            "coverage_score": 0,
            "missing_entities": [],
            "missing_relationships": [],
            "cardinality_issues": [],
            "orphaned_entities": [],
            "missing_attributes": [],
            "recommendations": []
        }


async def run_full_analysis(image_path: str, user_stories: str) -> tuple[dict, dict]:
    """Run the complete two-step analysis."""
    # Step 1: Extract ERD from image
    extracted_erd = extract_erd_from_image(image_path)

    # Step 2: Compare against user stories
    report = analyze_erd_against_stories(extracted_erd, user_stories)

    return extracted_erd, report
