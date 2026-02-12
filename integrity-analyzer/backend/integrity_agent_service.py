import os
import json
import anthropic
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from pathlib import Path

# Initialize Anthropic client
client = anthropic.Anthropic()

# File extensions for different languages
CODE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.cs': 'csharp',
    '.go': 'go',
    '.rb': 'ruby',
    '.php': 'php',
    '.rs': 'rust',
    '.cpp': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.hpp': 'cpp',
}

CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.env', '.config'}
DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc'}

# Security-relevant keywords for scoring
SECURITY_KEYWORDS = {
    'auth', 'login', 'password', 'token', 'jwt', 'oauth', 'session',
    'encrypt', 'decrypt', 'hash', 'secret', 'key', 'credential',
    'permission', 'role', 'access', 'grant', 'deny', 'authorize',
    'sanitize', 'validate', 'escape', 'filter', 'input',
    'log', 'audit', 'track', 'monitor', 'record',
    'sql', 'query', 'database', 'inject', 'xss', 'csrf',
    'secure', 'security', 'protect', 'guard', 'middleware'
}


@dataclass
class DiscoveredFileInfo:
    file_path: str
    file_type: str
    language: Optional[str]
    relevance_score: int
    content_preview: Optional[str]


@dataclass
class CharacteristicFinding:
    finding_type: str  # 'positive', 'negative', 'warning'
    file_path: str
    line_number: Optional[int]
    code_snippet: Optional[str]
    explanation: str


@dataclass
class CharacteristicReport:
    characteristic: str
    score: float
    status: str
    description: str
    findings: List[Dict]
    recommendations: List[str]


@dataclass
class IntegrityAnalysisResult:
    confidentiality: CharacteristicReport
    data_integrity: CharacteristicReport
    authenticity: CharacteristicReport
    non_repudiation: CharacteristicReport
    accountability: CharacteristicReport
    resistance: CharacteristicReport
    overall_score: float
    summary: Dict


def calculate_relevance_score(file_path: str, content: str) -> int:
    """Calculate security relevance score based on file path and content."""
    score = 50  # Base score

    path_lower = file_path.lower()
    content_lower = content.lower()

    # Boost for security-related paths
    security_paths = ['auth', 'security', 'middleware', 'guard', 'permission', 'login', 'session']
    for term in security_paths:
        if term in path_lower:
            score += 15
            break

    # Boost for configuration files
    if any(ext in path_lower for ext in ['.env', 'config', 'settings']):
        score += 10

    # Count security keywords in content
    keyword_count = sum(1 for kw in SECURITY_KEYWORDS if kw in content_lower)
    score += min(keyword_count * 3, 30)  # Max 30 points from keywords

    # Penalize test files (less relevant for production security)
    if 'test' in path_lower or 'spec' in path_lower or 'mock' in path_lower:
        score -= 20

    # Penalize node_modules, vendor, etc.
    if 'node_modules' in path_lower or 'vendor' in path_lower or '__pycache__' in path_lower:
        score = 0

    return max(0, min(100, score))


async def discover_files(repo_path: str) -> List[DiscoveredFileInfo]:
    """
    Agent 1: File Discovery Agent
    Scans the repository and identifies relevant files for security analysis.
    """
    discovered_files = []
    repo_path = Path(repo_path)

    # Walk through the repository
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-relevant directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                   {'node_modules', 'vendor', '__pycache__', 'venv', '.venv', 'dist', 'build', 'target'}]

        for file in files:
            if file.startswith('.'):
                continue

            file_path = Path(root) / file
            rel_path = file_path.relative_to(repo_path)
            ext = file_path.suffix.lower()

            # Determine file type and language
            if ext in CODE_EXTENSIONS:
                file_type = 'code'
                language = CODE_EXTENSIONS[ext]
            elif ext in CONFIG_EXTENSIONS:
                file_type = 'config'
                language = None
            elif ext in DOC_EXTENSIONS:
                file_type = 'documentation'
                language = None
            else:
                continue  # Skip unknown file types

            # Read file content for analysis
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Skip very large files
                if len(content) > 100000:
                    content = content[:100000]

                # Calculate relevance score
                relevance_score = calculate_relevance_score(str(rel_path), content)

                # Skip files with very low relevance
                if relevance_score < 10:
                    continue

                # Get content preview
                preview = content[:500] if len(content) > 500 else content

                discovered_files.append(DiscoveredFileInfo(
                    file_path=str(rel_path),
                    file_type=file_type,
                    language=language,
                    relevance_score=relevance_score,
                    content_preview=preview
                ))

            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                continue

    # Sort by relevance score (highest first)
    discovered_files.sort(key=lambda x: x.relevance_score, reverse=True)

    # Return top 100 most relevant files
    return discovered_files[:100]


def read_file_content(repo_path: str, file_path: str) -> str:
    """Read the full content of a file."""
    full_path = Path(repo_path) / file_path
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def parse_json_response(response_text: str) -> Dict:
    """Parse JSON from Claude's response, handling markdown code blocks."""
    text = response_text.strip()

    # Try to extract JSON from markdown code block
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        if end > start:
            text = text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        if end > start:
            text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response text: {text[:500]}")
        return {}


async def analyze_confidentiality(repo_path: str, files: List[Dict]) -> CharacteristicReport:
    """
    Agent 2a: Confidentiality Analysis
    Analyzes whether unauthorized users cannot access private data.
    """
    # Prepare file contents for analysis
    file_contents = []
    for f in files[:30]:  # Limit to top 30 files
        content = read_file_content(repo_path, f['file_path'])
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"
        file_contents.append({
            'path': f['file_path'],
            'content': content
        })

    prompt = f"""Analyze the following codebase for CONFIDENTIALITY - whether unauthorized users cannot access private data.

Look for:
1. Access control mechanisms (role-based access, permissions)
2. Data encryption (at rest and in transit)
3. Secure storage of sensitive data (passwords, tokens, API keys)
4. Environment variable usage for secrets
5. Proper visibility/scope of sensitive functions and data
6. Session management and token handling

For each finding, provide:
- The specific file and line number (if identifiable)
- A relevant code snippet (max 5 lines)
- Explanation of whether it supports or undermines confidentiality

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of confidentiality posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for confidentiality>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    result = parse_json_response(response.content[0].text)

    return CharacteristicReport(
        characteristic="Confidentiality",
        score=result.get('score', 50),
        status=result.get('status', 'partially_fulfilled'),
        description=result.get('description', 'Analysis incomplete'),
        findings=result.get('findings', []),
        recommendations=result.get('recommendations', [])
    )


async def analyze_data_integrity(repo_path: str, files: List[Dict]) -> CharacteristicReport:
    """
    Agent 2b: Data Integrity Analysis
    Analyzes whether data cannot be modified without authorization and validations prevent corruption.
    """
    file_contents = []
    for f in files[:30]:
        content = read_file_content(repo_path, f['file_path'])
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"
        file_contents.append({
            'path': f['file_path'],
            'content': content
        })

    prompt = f"""Analyze the following codebase for DATA INTEGRITY - whether data cannot be modified without authorization and validations prevent corruption.

Look for:
1. Input validation (type checking, format validation, range checks)
2. Data sanitization before storage
3. Database constraints and transactions
4. Immutability patterns where appropriate
5. Checksums or hashes for data verification
6. Proper error handling that prevents partial updates
7. Authorization checks before data modification

For each finding, provide specific file locations and code snippets.

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of data integrity posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for data integrity>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    result = parse_json_response(response.content[0].text)

    return CharacteristicReport(
        characteristic="Data Integrity",
        score=result.get('score', 50),
        status=result.get('status', 'partially_fulfilled'),
        description=result.get('description', 'Analysis incomplete'),
        findings=result.get('findings', []),
        recommendations=result.get('recommendations', [])
    )


async def analyze_authenticity(repo_path: str, files: List[Dict]) -> CharacteristicReport:
    """
    Agent 2c: Authenticity Analysis
    Analyzes whether users are who they claim to be (authentication mechanisms).
    """
    file_contents = []
    for f in files[:30]:
        content = read_file_content(repo_path, f['file_path'])
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"
        file_contents.append({
            'path': f['file_path'],
            'content': content
        })

    prompt = f"""Analyze the following codebase for AUTHENTICITY - whether users are who they claim to be.

Look for:
1. Authentication mechanisms (OAuth, JWT, session-based, API keys)
2. Password hashing algorithms (bcrypt, argon2, etc.)
3. Multi-factor authentication support
4. Token validation and verification
5. Identity provider integration
6. Secure password reset flows
7. Session invalidation on logout

For each finding, provide specific file locations and code snippets.

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of authenticity posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for authenticity>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    result = parse_json_response(response.content[0].text)

    return CharacteristicReport(
        characteristic="Authenticity",
        score=result.get('score', 50),
        status=result.get('status', 'partially_fulfilled'),
        description=result.get('description', 'Analysis incomplete'),
        findings=result.get('findings', []),
        recommendations=result.get('recommendations', [])
    )


async def analyze_non_repudiation(repo_path: str, files: List[Dict]) -> CharacteristicReport:
    """
    Agent 2d: Non-Repudiation Analysis
    Analyzes whether actions are logged and traceable to specific users.
    """
    file_contents = []
    for f in files[:30]:
        content = read_file_content(repo_path, f['file_path'])
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"
        file_contents.append({
            'path': f['file_path'],
            'content': content
        })

    prompt = f"""Analyze the following codebase for NON-REPUDIATION - whether actions are logged and traceable to specific users, preventing denial of actions.

Look for:
1. Audit logging with user identification
2. Timestamped action records
3. Digital signatures for critical operations
4. Immutable audit trails
5. Transaction logging
6. Request/response logging with user context
7. Event sourcing patterns

For each finding, provide specific file locations and code snippets.

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of non-repudiation posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for non-repudiation>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    result = parse_json_response(response.content[0].text)

    return CharacteristicReport(
        characteristic="Non-Repudiation",
        score=result.get('score', 50),
        status=result.get('status', 'partially_fulfilled'),
        description=result.get('description', 'Analysis incomplete'),
        findings=result.get('findings', []),
        recommendations=result.get('recommendations', [])
    )


async def analyze_accountability(repo_path: str, files: List[Dict]) -> CharacteristicReport:
    """
    Agent 2e: Accountability Analysis
    Analyzes whether the system tracks who did what and when.
    """
    file_contents = []
    for f in files[:30]:
        content = read_file_content(repo_path, f['file_path'])
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"
        file_contents.append({
            'path': f['file_path'],
            'content': content
        })

    prompt = f"""Analyze the following codebase for ACCOUNTABILITY - whether the system tracks who did what and when.

Look for:
1. User action logging
2. Created_by/updated_by fields in data models
3. Timestamp tracking (created_at, updated_at)
4. Change history/versioning
5. Activity feeds or history endpoints
6. User session tracking
7. Administrative action logging

For each finding, provide specific file locations and code snippets.

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of accountability posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for accountability>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    result = parse_json_response(response.content[0].text)

    return CharacteristicReport(
        characteristic="Accountability",
        score=result.get('score', 50),
        status=result.get('status', 'partially_fulfilled'),
        description=result.get('description', 'Analysis incomplete'),
        findings=result.get('findings', []),
        recommendations=result.get('recommendations', [])
    )


async def analyze_resistance(repo_path: str, files: List[Dict]) -> CharacteristicReport:
    """
    Agent 2f: Resistance Analysis
    Analyzes whether the system resists attacks (SQL injection, XSS, parameter tampering).
    """
    file_contents = []
    for f in files[:30]:
        content = read_file_content(repo_path, f['file_path'])
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"
        file_contents.append({
            'path': f['file_path'],
            'content': content
        })

    prompt = f"""Analyze the following codebase for RESISTANCE - whether the system resists common attacks.

Look for vulnerabilities and protections against:
1. SQL Injection (parameterized queries, ORMs, raw SQL usage)
2. XSS (Cross-Site Scripting) - output encoding, CSP headers, sanitization
3. CSRF (Cross-Site Request Forgery) - token validation, SameSite cookies
4. Parameter tampering - server-side validation, type checking
5. Path traversal - file path validation
6. Command injection - shell command safety
7. Insecure deserialization
8. Security headers (CORS, CSP, X-Frame-Options)

For each finding, provide specific file locations and code snippets.

Files to analyze:
{json.dumps(file_contents, indent=2)}

Respond with a JSON object:
{{
    "score": <0-100 score>,
    "status": "<fulfilled|partially_fulfilled|not_fulfilled|not_applicable>",
    "description": "<2-3 sentence summary of attack resistance posture>",
    "findings": [
        {{
            "type": "<positive|negative|warning>",
            "file_path": "<path>",
            "line_number": <number or null>,
            "code_snippet": "<relevant code>",
            "explanation": "<what this means for attack resistance>"
        }}
    ],
    "recommendations": ["<actionable recommendation>", ...]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    result = parse_json_response(response.content[0].text)

    return CharacteristicReport(
        characteristic="Resistance",
        score=result.get('score', 50),
        status=result.get('status', 'partially_fulfilled'),
        description=result.get('description', 'Analysis incomplete'),
        findings=result.get('findings', []),
        recommendations=result.get('recommendations', [])
    )


async def generate_summary(reports: List[CharacteristicReport]) -> Dict:
    """
    Agent 3: Summary Generation
    Generates an overall summary based on all characteristic analyses.
    """
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

    prompt = f"""Based on the following integrity analysis results, generate an executive summary.

Analysis Results:
{json.dumps(reports_data, indent=2)}

Provide:
1. An overall integrity score (weighted average, with Resistance and Confidentiality weighted higher)
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

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    return parse_json_response(response.content[0].text)


async def run_integrity_analysis(repo_path: str, selected_files: List[Dict]) -> IntegrityAnalysisResult:
    """
    Main orchestrator: Runs the complete integrity analysis workflow.
    """
    # Convert files to list of dicts if needed
    files = [{'file_path': f['file_path'], 'file_type': f['file_type']} for f in selected_files]

    # Run all characteristic analyses
    confidentiality = await analyze_confidentiality(repo_path, files)
    data_integrity = await analyze_data_integrity(repo_path, files)
    authenticity = await analyze_authenticity(repo_path, files)
    non_repudiation = await analyze_non_repudiation(repo_path, files)
    accountability = await analyze_accountability(repo_path, files)
    resistance = await analyze_resistance(repo_path, files)

    # Generate summary
    all_reports = [confidentiality, data_integrity, authenticity, non_repudiation, accountability, resistance]
    summary = await generate_summary(all_reports)

    return IntegrityAnalysisResult(
        confidentiality=confidentiality,
        data_integrity=data_integrity,
        authenticity=authenticity,
        non_repudiation=non_repudiation,
        accountability=accountability,
        resistance=resistance,
        overall_score=summary.get('overall_score', 50),
        summary=summary
    )
