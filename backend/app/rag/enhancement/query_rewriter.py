from app.rag.generation.generator import client
import re

QUERY_ENHANCEMENT_SYSTEM_PROMPT = """You are a financial search query optimizer for loan and retail credit agreements.
Your goal is to transform the user's raw question into a concise, high-precision search query (3 to 8 words) for hybrid vector and BM25 document retrieval.

STRICT RULES:
1. PRESERVE CORE INTENT: Keep the exact financial entity requested (e.g. if the user asks for "interest rate", search for "interest rate", DO NOT substitute it with "APR").
2. NO CHATTY BOILERPLATE: Output ONLY the search query string. Never output explanations, quotes, or conversational phrases.
3. CONTRACT SYNONYMS: Append 2-3 standard contractual terms or section headers (e.g. "per annum", "charges", "tenure months", "schedule").
4. CONCISE & DENSE: Limit the output strictly to 3 to 8 keywords.

FEW-SHOT EXAMPLES:
User: "what is the interest rate"
Search Query: interest rate per annum fixed floating percentage

User: "what is the processing fee"
Search Query: processing fee upfront administrative charges

User: "can I close my loan early"
Search Query: prepayment penalty foreclosure charges early repayment

User: "what if I miss a payment"
Search Query: late payment fee penalty overdue interest bounce charges

User: "how much is the monthly EMI"
Search Query: monthly EMI installment repayment schedule amount

User: "what is the tenure"
Search Query: loan tenure repayment period duration months

User: "give me the confidence score and risk factors"
Search Query: loan agreement risk factors penalty terms default conditions
"""

def rewrite_query(query: str, intent: str = "general") -> str:
    """
    Enhance the user's query with targeted domain keywords using LLM-driven reasoning.
    """
    q_clean = query.strip()
    if not q_clean:
        return query

    prompt = f'Intent: {intent}\nUser: "{q_clean}"\nSearch Query:'

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": QUERY_ENHANCEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=30,
        )
        rewritten = response.choices[0].message.content.strip()
        # Clean any quotes or prefixes
        rewritten = re.sub(r'^["\']|["\']$', '', rewritten).strip()
        if rewritten.lower().startswith("search query:"):
            rewritten = rewritten[len("search query:"):].strip()

        return rewritten if rewritten else q_clean
    except Exception:
        return q_clean  # Safe fallback to original on connection issue