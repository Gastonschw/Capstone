"""Extract analysis-ready text from source files and attached project documents."""

import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader


DOCUMENT_EXTENSIONS = {".docx", ".pdf"}
NOTEBOOK_EXTENSIONS = {".ipynb"}


def _extract_notebook(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = []
    for index, cell in enumerate(notebook.get("cells", []), start=1):
        cell_type = cell.get("cell_type")
        if cell_type not in {"markdown", "code"}:
            continue
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if text.strip():
            cells.append(f"## {cell_type.title()} cell {index}\n{text}")
    return "\n\n".join(cells)


def _extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as document:
        root = ElementTree.fromstring(document.read("word/document.xml"))
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
        if text.strip():
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pdf(path: Path) -> str:
    pages = []
    for index, page in enumerate(PdfReader(path).pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"## Page {index}\n{text}")
    return "\n\n".join(pages)


def read_file_content(file_path: str | Path, max_chars: int | None = None) -> str:
    """Return readable source content; notebook outputs are intentionally excluded."""
    path = Path(file_path)
    try:
        suffix = path.suffix.lower()
        if suffix in NOTEBOOK_EXTENSIONS:
            content = _extract_notebook(path)
        elif suffix == ".docx":
            content = _extract_docx(path)
        elif suffix == ".pdf":
            content = _extract_pdf(path)
        else:
            content = path.read_text(encoding="utf-8", errors="ignore").replace("\x00", "")
    except Exception as exc:
        return f"[Error reading file: {exc}]"

    if max_chars is not None and len(content) > max_chars:
        return content[:max_chars] + "\n... (truncated)"
    return content
