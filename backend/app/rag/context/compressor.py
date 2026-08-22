from typing import List, Dict, Any
from app.rag.generation.generator import client

def compress_context(question: str, chunks: List[Dict[str, Any]], max_length: int = 2000) -> str:
    """
    Compresses retrieved chunks by extracting only sentences relevant to the question.
    Falls back to simple concatenation if LLM compression is unavailable.
    """
    raw_text = "\n\n".join([c.get("text", "") for c in chunks])
    if len(raw_text) <= max_length:
        return raw_text

    prompt = f"""Given the question: "{question}"
Extract and synthesize only the relevant sentences and factual claims from the excerpts below:

{raw_text[:4000]}

Extracted relevant context:"""
    try:
        if client:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
    except Exception:
        pass
    
    return raw_text[:max_length]
