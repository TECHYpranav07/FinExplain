from app.rag.generation.generator import client
import re

def rewrite_query(query: str, intent: str = "general") -> str:
    """
    Rewrite the user's query to improve retrieval precision.
    Preserves specific factual queries directly while expanding vague or short queries.
    """
    q_clean = query.strip()
    q_lower = q_clean.lower()

    # Fast deterministic passthrough for standard factual contract terms
    if any(k in q_lower for k in (
        "interest rate", "rate of interest", "processing fee", "documentation fee",
        "late payment", "prepayment", "foreclosure", "tenure", "emi", "apr",
        "penal charge", "bounce fee", "grace period"
    )):
        return q_clean

    prompt = f"""
Rewrite the following user question to make it more specific and searchable for a loan document retrieval system.

Original: "{query}"
Intent: {intent}

Requirements:
- Keep the core meaning intact.
- Replace vague terms with specific financial terms.
- Make it concise and keyword-rich for a vector search.
- Add context about loan products if relevant.

Return ONLY the rewritten query, nothing else.
"""
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100
        )
        rewritten = response.choices[0].message.content.strip()
        return rewritten if rewritten else query
    except Exception:
        return query  # Fallback to original