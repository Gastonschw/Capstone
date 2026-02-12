"""
Agentic Workflow Service

Implements multi-agent workflow for repository analysis:
1. File Discovery Agent - finds ERD images and user story files
2. ERD to UML Agent - converts ERD diagrams to structured UML
3. Analysis Agent - analyzes UML against user stories
"""

import anthropic
import base64
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from models import Repository, DiscoveredFile, FileType


def get_client():
    return anthropic.Anthropic()


# ============== File Type Detection ==============

# Image extensions for ERD detection
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}

# Text file extensions for user story detection
TEXT_EXTENSIONS = {'.md', '.txt', '.rst', '.feature', '.story', '.adoc'}

# Directories likely to contain ERD diagrams
ERD_DIRECTORY_HINTS = {'diagrams', 'erd', 'database', 'db', 'schema', 'models', 'docs', 'documentation', 'design', 'architecture'}

# Directories likely to contain user stories
STORY_DIRECTORY_HINTS = {'stories', 'user-stories', 'userstories', 'requirements', 'specs', 'features', 'docs', 'documentation'}


@dataclass
class FileCandidate:
    """A file candidate for analysis."""
    path: str
    file_type: str
    confidence: int
    preview: Optional[str] = None


# ============== Agent 1: File Discovery Agent ==============

def scan_repository_files(repo_path: str) -> Dict[str, List[str]]:
    """
    Scan a repository and categorize files by type.
    Returns dict with 'images' and 'text_files' lists.
    """
    repo = Path(repo_path)
    
    images = []
    text_files = []
    
    for file_path in repo.rglob('*'):
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            relative_path = str(file_path.relative_to(repo))
            
            if suffix in IMAGE_EXTENSIONS:
                images.append(relative_path)
            elif suffix in TEXT_EXTENSIONS:
                text_files.append(relative_path)
    
    return {
        'images': images,
        'text_files': text_files
    }


def score_erd_candidate(file_path: str) -> int:
    """
    Score how likely a file is an ERD diagram based on path and name.
    Returns 0-100 confidence score.
    """
    path_lower = file_path.lower()
    path_parts = Path(file_path).parts
    
    score = 50  # Base score for any image
    
    # Check directory hints
    for part in path_parts[:-1]:  # Exclude filename
        if part.lower() in ERD_DIRECTORY_HINTS:
            score += 20
            break
    
    # Check filename hints
    filename = Path(file_path).stem.lower()
    erd_keywords = ['erd', 'entity', 'relationship', 'database', 'schema', 'diagram', 'db', 'model', 'data']
    
    for keyword in erd_keywords:
        if keyword in filename:
            score += 15
            break
    
    # Boost if in root or docs folder
    if len(path_parts) <= 2:
        score += 10
    
    return min(score, 100)


def score_user_story_candidate(file_path: str, content: str) -> int:
    """
    Score how likely a file contains user stories based on path, name, and content.
    Returns 0-100 confidence score.
    """
    path_lower = file_path.lower()
    path_parts = Path(file_path).parts
    
    score = 30  # Base score for any text file
    
    # Check directory hints
    for part in path_parts[:-1]:
        if part.lower() in STORY_DIRECTORY_HINTS:
            score += 15
            break
    
    # Check filename hints
    filename = Path(file_path).stem.lower()
    story_keywords = ['story', 'stories', 'requirement', 'feature', 'user', 'acceptance', 'spec']
    
    for keyword in story_keywords:
        if keyword in filename:
            score += 15
            break
    
    # Content analysis
    content_lower = content.lower()
    
    # User story patterns
    if 'as a ' in content_lower and ' i want ' in content_lower:
        score += 25
    elif 'as a ' in content_lower:
        score += 15
    
    # Gherkin patterns
    if 'given ' in content_lower and 'when ' in content_lower and 'then ' in content_lower:
        score += 25
    
    # Acceptance criteria patterns
    if 'acceptance criteria' in content_lower:
        score += 20
    
    # Check for common requirement keywords
    requirement_keywords = ['shall', 'must', 'should', 'requirement', 'feature', 'scenario']
    for keyword in requirement_keywords:
        if keyword in content_lower:
            score += 5
            break
    
    return min(score, 100)


async def discover_files_with_ai(
    repo_path: str,
    images: List[str],
    text_files: List[str]
) -> Dict[str, List[FileCandidate]]:
    """
    Use AI to intelligently identify ERD images and user story files.
    """
    client = get_client()
    repo = Path(repo_path)
    
    # Prepare file list for AI analysis
    file_info = []
    for img in images[:50]:  # Limit to 50 images
        file_info.append({"path": img, "type": "image"})
    
    text_previews = []
    for txt in text_files[:30]:  # Limit to 30 text files
        txt_path = repo / txt
        try:
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)  # First 1000 chars
            text_previews.append({"path": txt, "type": "text", "preview": content[:500]})
            file_info.append({"path": txt, "type": "text", "preview": content[:200]})
        except Exception:
            continue
    
    # Use AI to identify relevant files
    discovery_prompt = f"""You are analyzing a software project repository to find:
1. ERD (Entity-Relationship Diagram) images - visual diagrams showing database structure
2. User Story files - documents containing user requirements in formats like:
   - "As a [user], I want [feature] so that [benefit]"
   - Gherkin format (Given/When/Then)
   - Acceptance criteria lists

Here are the files in the repository:

## Image Files:
{json.dumps([f["path"] for f in file_info if f["type"] == "image"], indent=2)}

## Text Files with Previews:
{json.dumps([{"path": f["path"], "preview": f.get("preview", "")[:200]} for f in file_info if f["type"] == "text"], indent=2)}

Analyze these files and return a JSON object identifying which files are most likely ERD diagrams and user stories:

{{
    "erd_images": [
        {{"path": "path/to/image.png", "confidence": 85, "reason": "brief reason"}}
    ],
    "user_story_files": [
        {{"path": "path/to/file.md", "confidence": 90, "reason": "brief reason"}}
    ]
}}

Only include files you're reasonably confident about (confidence > 50).
Return ONLY the JSON object, no other text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": discovery_prompt}
        ],
    )
    
    response_text = message.content[0].text
    
    try:
        # Parse JSON response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        ai_results = json.loads(response_text.strip())
    except json.JSONDecodeError:
        ai_results = {"erd_images": [], "user_story_files": []}
    
    # Build final candidates with AI and heuristic scores
    erd_candidates = []
    for item in ai_results.get("erd_images", []):
        erd_candidates.append(FileCandidate(
            path=item["path"],
            file_type=FileType.erd_image.value,
            confidence=item.get("confidence", 70)
        ))
    
    # Add high-scoring heuristic candidates not found by AI
    for img in images:
        heuristic_score = score_erd_candidate(img)
        if heuristic_score >= 70 and not any(c.path == img for c in erd_candidates):
            erd_candidates.append(FileCandidate(
                path=img,
                file_type=FileType.erd_image.value,
                confidence=heuristic_score
            ))
    
    story_candidates = []
    for item in ai_results.get("user_story_files", []):
        # Get content preview
        preview = ""
        for tp in text_previews:
            if tp["path"] == item["path"]:
                preview = tp.get("preview", "")[:500]
                break
        
        story_candidates.append(FileCandidate(
            path=item["path"],
            file_type=FileType.user_story.value,
            confidence=item.get("confidence", 70),
            preview=preview
        ))
    
    # Add high-scoring heuristic candidates
    for txt_info in text_previews:
        txt = txt_info["path"]
        content = txt_info.get("preview", "")
        heuristic_score = score_user_story_candidate(txt, content)
        if heuristic_score >= 65 and not any(c.path == txt for c in story_candidates):
            story_candidates.append(FileCandidate(
                path=txt,
                file_type=FileType.user_story.value,
                confidence=heuristic_score,
                preview=content[:500]
            ))
    
    # Sort by confidence
    erd_candidates.sort(key=lambda x: x.confidence, reverse=True)
    story_candidates.sort(key=lambda x: x.confidence, reverse=True)
    
    return {
        "erd_images": erd_candidates[:10],  # Top 10 ERD candidates
        "user_story_files": story_candidates[:15]  # Top 15 user story candidates
    }


async def run_file_discovery(repo_path: str, db: Session, repository_id: int) -> Dict[str, Any]:
    """
    Run the complete file discovery workflow and save results to database.
    """
    # Step 1: Scan for all files
    files = scan_repository_files(repo_path)
    
    # Step 2: Use AI + heuristics to identify relevant files
    discovered = await discover_files_with_ai(
        repo_path,
        files['images'],
        files['text_files']
    )
    
    # Step 3: Save discovered files to database
    saved_files = []
    
    for candidate in discovered['erd_images']:
        db_file = DiscoveredFile(
            repository_id=repository_id,
            file_path=candidate.path,
            file_type=candidate.file_type,
            confidence_score=candidate.confidence,
            is_selected=candidate.confidence >= 60
        )
        db.add(db_file)
        saved_files.append(db_file)
    
    for candidate in discovered['user_story_files']:
        db_file = DiscoveredFile(
            repository_id=repository_id,
            file_path=candidate.path,
            file_type=candidate.file_type,
            confidence_score=candidate.confidence,
            content_preview=candidate.preview,
            is_selected=candidate.confidence >= 60
        )
        db.add(db_file)
        saved_files.append(db_file)
    
    db.commit()
    
    return {
        "erd_images_found": len(discovered['erd_images']),
        "user_story_files_found": len(discovered['user_story_files']),
        "total_files_scanned": len(files['images']) + len(files['text_files'])
    }


# ============== Agent 2: ERD to UML Extraction ==============

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


async def extract_uml_from_erd(image_path: str) -> Dict[str, Any]:
    """
    Extract detailed UML structure from an ERD image.
    
    Returns structured UML format with:
    - classes: name, attributes (with visibility, type, keys), methods
    - associations: source, target, type, multiplicities
    - generalizations: inheritance relationships
    """
    client = get_client()
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
    
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        return {
            "raw_extraction": response_text,
            "classes": [],
            "associations": [],
            "generalizations": [],
            "notes": ["Failed to parse structured output"]
        }


async def extract_uml_from_multiple_images(image_paths: List[str]) -> Dict[str, Any]:
    """
    Extract and merge UML structures from multiple ERD images.
    """
    all_classes = []
    all_associations = []
    all_generalizations = []
    all_notes = []
    
    for image_path in image_paths:
        try:
            uml = await extract_uml_from_erd(image_path)
            
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


# ============== Agent 3: Analysis Agent ==============

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


async def analyze_uml_against_stories(uml_structure: Dict[str, Any], user_stories: str) -> Dict[str, Any]:
    """
    Analyze UML structure against user stories to find coverage issues.
    Enhanced version that works with the new UML structure format.
    """
    client = get_client()
    
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

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": analysis_prompt}
        ],
    )
    
    response_text = message.content[0].text
    
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
            "data_integrity_concerns": [],
            "recommendations": [],
            "user_story_coverage": []
        }


# ============== Orchestrator: Coordinate Full Workflow ==============

@dataclass
class WorkflowResult:
    """Result of the complete analysis workflow."""
    success: bool
    uml_structure: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    discovery_stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


async def run_repository_analysis(
    repository: Repository,
    db: Session,
    use_selected_files_only: bool = True
) -> WorkflowResult:
    """
    Run the complete agentic workflow on a repository:
    
    1. File Discovery - Find ERD images and user story files
    2. ERD to UML - Extract UML structure from discovered ERD images  
    3. Analysis - Compare UML against user stories
    
    Args:
        repository: The repository to analyze
        db: Database session
        use_selected_files_only: If True, only use files marked as selected
    
    Returns:
        WorkflowResult with UML structure and analysis report
    """
    repo_path = repository.local_path
    
    try:
        # Step 1: Check if files already discovered, if not run discovery
        existing_files = db.query(DiscoveredFile).filter(
            DiscoveredFile.repository_id == repository.id
        ).all()
        
        if not existing_files:
            # Run file discovery
            discovery_stats = await run_file_discovery(repo_path, db, repository.id)
            
            # Refresh the file list
            existing_files = db.query(DiscoveredFile).filter(
                DiscoveredFile.repository_id == repository.id
            ).all()
        else:
            discovery_stats = {
                "erd_images_found": len([f for f in existing_files if f.file_type == FileType.erd_image.value]),
                "user_story_files_found": len([f for f in existing_files if f.file_type == FileType.user_story.value]),
                "from_cache": True
            }
        
        # Filter files based on selection
        if use_selected_files_only:
            erd_files = [f for f in existing_files 
                        if f.file_type == FileType.erd_image.value and f.is_selected]
            story_files = [f for f in existing_files 
                          if f.file_type == FileType.user_story.value and f.is_selected]
        else:
            erd_files = [f for f in existing_files if f.file_type == FileType.erd_image.value]
            story_files = [f for f in existing_files if f.file_type == FileType.user_story.value]
        
        # Validate we have required files
        if not erd_files:
            return WorkflowResult(
                success=False,
                error="No ERD images found or selected in the repository. Please upload a repository containing ERD diagram images.",
                discovery_stats=discovery_stats
            )
        
        if not story_files:
            return WorkflowResult(
                success=False,
                error="No user story files found or selected in the repository. Please ensure your repository contains user story documentation.",
                discovery_stats=discovery_stats
            )
        
        # Step 2: Extract UML from ERD images
        erd_image_paths = [
            str(Path(repo_path) / f.file_path) 
            for f in erd_files
        ]
        
        uml_structure = await extract_uml_from_multiple_images(erd_image_paths)
        
        # Validate UML extraction
        if not uml_structure.get("classes"):
            return WorkflowResult(
                success=False,
                error="Failed to extract any entities from the ERD images. Please ensure the images contain valid ERD diagrams.",
                uml_structure=uml_structure,
                discovery_stats=discovery_stats
            )
        
        # Step 3: Read user stories
        story_file_paths = [f.file_path for f in story_files]
        user_stories = read_user_stories_from_files(repo_path, story_file_paths)
        
        if not user_stories.strip():
            return WorkflowResult(
                success=False,
                error="User story files were found but appear to be empty.",
                uml_structure=uml_structure,
                discovery_stats=discovery_stats
            )
        
        # Step 4: Run analysis
        report = await analyze_uml_against_stories(uml_structure, user_stories)
        
        return WorkflowResult(
            success=True,
            uml_structure=uml_structure,
            report=report,
            discovery_stats=discovery_stats
        )
        
    except Exception as e:
        return WorkflowResult(
            success=False,
            error=f"Analysis workflow failed: {str(e)}"
        )


async def run_discovery_only(repository: Repository, db: Session) -> Dict[str, Any]:
    """
    Run only the file discovery step without full analysis.
    Useful for letting users review and select files before analysis.
    """
    # Clear existing discovered files
    db.query(DiscoveredFile).filter(
        DiscoveredFile.repository_id == repository.id
    ).delete()
    db.commit()
    
    # Run discovery
    return await run_file_discovery(repository.local_path, db, repository.id)
