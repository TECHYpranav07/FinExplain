import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
import io
import re


# ---------------------------------------------------------------------------
# Section-heading detection helpers
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    # "Effective Date: 01 Jan 2025" or "Effective Date: 2025-01-01"
    re.compile(
        r"[Ee]ffective\s+[Dd]ate\s*[:]\s*(\d{1,2}[\s/\-]\w+[\s/\-]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2})"
    ),
    # "Date: ..."
    re.compile(
        r"(?<![a-zA-Z])[Dd]ate\s*[:]\s*(\d{1,2}[\s/\-]\w+[\s/\-]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2})"
    ),
]

_VERSION_PATTERN = re.compile(
    r"[Vv]ersion\s*[:.]?\s*([\d]+(?:\.[\d]+)*)", re.IGNORECASE
)


def _detect_document_metadata(full_text: str) -> Dict[str, Optional[str]]:
    """Scan the full document text for effective date and version strings."""
    metadata: Dict[str, Optional[str]] = {
        "effective_date": None,
        "document_version": None,
        "document_date": None,
    }

    for pattern in _DATE_PATTERNS:
        match = pattern.search(full_text)
        if match:
            if "effective" in pattern.pattern.lower():
                metadata["effective_date"] = match.group(1).strip()
            else:
                metadata["document_date"] = match.group(1).strip()

    version_match = _VERSION_PATTERN.search(full_text)
    if version_match:
        metadata["document_version"] = version_match.group(1).strip()

    return metadata


def _extract_sections_from_page(page: fitz.Page) -> List[Dict[str, Any]]:
    """
    Use font-size heuristics to identify section headings on a page.

    Returns a list of ``{"title": str, "font_size": float}`` dicts for every
    text span whose font size is noticeably larger than the median on the page,
    or that uses bold formatting.
    """
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])

    # Collect all span font sizes to compute the median
    all_sizes: List[float] = []
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text", "").strip():
                    all_sizes.append(span["size"])

    if not all_sizes:
        return []

    all_sizes.sort()
    median_size = all_sizes[len(all_sizes) // 2]

    # Threshold: a span is a heading if its font size is ≥ 1.15× the median
    # or if it is bold.
    heading_threshold = median_size * 1.15

    headings: List[Dict[str, Any]] = []
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text or len(text) < 2:
                    continue
                is_bold = bool(span.get("flags", 0) & 2 ** 4)  # bit 4 = bold
                if span["size"] >= heading_threshold or is_bold:
                    # Avoid treating very long paragraphs as headings
                    if len(text) < 200:
                        headings.append({
                            "title": text,
                            "font_size": span["size"],
                        })
    return headings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parse a PDF file and extract text with page numbers, section headings,
    and document-level metadata.

    Returns::

        {
            "full_text": "...",
            "pages": [
                {
                    "page_num": 1,
                    "text": "...",
                    "sections": [{"title": "...", "font_size": 12.0}, ...]
                },
                ...
            ],
            "total_pages": 10,
            "document_metadata": {
                "effective_date": "01 Jan 2025" | None,
                "document_version": "2.1" | None,
                "document_date": "2025-01-01" | None,
            }
        }
    """
    doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")

    pages: List[Dict[str, Any]] = []
    full_text = ""

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        if not text.strip():
            continue

        # Extract section headings from the page
        sections = _extract_sections_from_page(page)

        pages.append({
            "page_num": page_num + 1,
            "text": text.strip(),
            "sections": sections,
        })
        full_text += f"\n\n--- Page {page_num + 1} ---\n\n{text}"

    doc.close()

    # Detect document-level metadata
    document_metadata = _detect_document_metadata(full_text)

    return {
        "full_text": full_text.strip(),
        "pages": pages,
        "total_pages": len(pages),
        "document_metadata": document_metadata,
    }