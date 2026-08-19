from app.rag.generation.generator import client
import json

def generate_multi_queries(query: str, num_queries: int = 3) -> list:
    """
    Generate multiple query variants for broader retrieval.
    """
    prompt = f"""
Given the user question: "{query}"
Generate {num_queries} alternative phrasings that capture different aspects of the question.

Return ONLY a JSON array of strings, e.g., ["query1", "query2", "query3"]
"""
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return [query]