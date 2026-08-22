from app.rag.generation.generator import client

def generate_hypothetical_document(query: str) -> str:
    """
    Generate a hypothetical document excerpt that would answer the query.
    """
    prompt = f"""
Generate a hypothetical excerpt from a loan document that would contain the answer to this question:
"{query}"

The excerpt should be realistic loan terms, fees, or conditions.
Return ONLY the hypothetical excerpt, nothing else.
"""
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return query