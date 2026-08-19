from app.rag.generation.generator import client

def rewrite_query(query: str, intent: str = "general") -> str:
    """
    Rewrite the user's query to improve retrieval precision.
    Uses the intent to guide rewriting.
    """
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
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
        rewritten = response.choices[0].message.content.strip()
        return rewritten if rewritten else query
    except Exception:
        return query  # Fallback to original