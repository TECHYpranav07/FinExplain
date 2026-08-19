from groq import Groq
from app.core.config import settings
from typing import Dict, Any

# Initialize Groq client
client = Groq(api_key=settings.GROQ_API_KEY)

def generate_answer(query: str, context: str) -> Dict[str, Any]:
    """
    Generate an answer using Groq Llama-3 with evidence-first prompting.
    """
    prompt = f"""
You are FinExplain, an AI assistant that helps consumers compare loan products. 
Your answers must be evidence-based, clear, and include citations.

CONTEXT:
{context}

USER QUESTION:
{query}

INSTRUCTIONS:
1. Answer the question using ONLY the provided context.
2. If the context does not contain the answer, say "Not specified in the provided documents."
3. For every factual statement, include a citation in square brackets: [Page X] or [Section Y].
4. If there are conflicting terms, mention both and flag the conflict.
5. Be concise but thorough.
6. Structure your answer with clear sections (e.g., Rates, Fees, Repayment Terms).

ANSWER:
"""
    
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are an evidence-first financial assistant. Never invent information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )
        
        answer_text = response.choices[0].message.content
        
        return {
            "answer": answer_text,
            "raw_response": response
        }
    
    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "error": str(e)
        }