import fitz  # PyMuPDF
from typing import List, Dict, Any
import io

def parse_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """
    Parse a PDF file and extract text with page numbers and basic structure.
    Returns: {
        "text": "full concatenated text",
        "pages": [{"page_num": 1, "text": "..."}, ...],
        "total_pages": 10
    }
    """
    doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
    
    pages = []
    full_text = ""
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        if text.strip():
            pages.append({
                "page_num": page_num + 1,
                "text": text.strip()
            })
            full_text += f"\n\n--- Page {page_num + 1} ---\n\n{text}"
    
    doc.close()
    
    return {
        "full_text": full_text.strip(),
        "pages": pages,
        "total_pages": len(pages)
    }