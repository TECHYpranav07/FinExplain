import re
from typing import List

def clean_text(text: str) -> str:
    """Normalize whitespace and strip extraneous control characters."""
    if not text:
        return ""
    text = re.sub(r'[\r\t]+', ' ', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def estimate_token_count(text: str) -> int:
    """Approximate token count (rule of thumb: 4 characters per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)

def extract_numeric_values(text: str) -> List[str]:
    """Extract numbers, percentages, and currencies from text."""
    pattern = r'(\$?\d+(?:,\d{3})*(?:\.\d+)?%?|\b\d+\b)'
    return re.findall(pattern, text)
