from app.rag.generation.generator import client
import json

def decompose_query(query: str) -> list:
    """
    Break complex questions into sub-questions.
    """
    prompt = f"""
The user asked: "{query}"
Break this down into 2-3 simpler sub-questions that would help answer the main question.

Return ONLY a JSON array of strings.
"""
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return [query]