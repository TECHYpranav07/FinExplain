from app.rag.generation.generator import client
import re

# Fast heuristic expansions (Zero LLM latency and zero token consumption)
FAST_KEYWORD_EXPANSIONS = [
    (re.compile(r"\b(?:interest\s*rate|rate\s*of\s*interest|roi|annual\s*rate)\b", re.IGNORECASE), "interest rate per annum fixed floating percentage benchmark"),
    (re.compile(r"\b(?:processing\s*fee|admin\s*fee|origination\s*fee)\b", re.IGNORECASE), "processing fee upfront administrative charges"),
    (re.compile(r"\b(?:documentation\s*fee|doc\s*fee|stamp\s*duty)\b", re.IGNORECASE), "documentation fee upfront administrative charges"),
    (re.compile(r"\b(?:prepayment|foreclosure|early\s*closure|close\s*early)\b", re.IGNORECASE), "prepayment penalty foreclosure charges early repayment"),
    (re.compile(r"\b(?:late\s*payment|delayed\s*payment|late\s*fee|miss\s*a\s*payment|bounce)\b", re.IGNORECASE), "late payment fee penalty overdue interest bounce charges"),
    (re.compile(r"\b(?:tenure|repayment\s*period|duration|months)\b", re.IGNORECASE), "loan tenure repayment period duration months"),
    (re.compile(r"\b(?:monthly\s*emi|emi|installment|instalment)\b", re.IGNORECASE), "monthly EMI installment repayment schedule amount"),
    (re.compile(r"\b(?:confidence\s*score|risk\s*score|risk\s*factor|risk\s*rating|how\s*risky)\b", re.IGNORECASE), "loan agreement risk factors penalty terms default conditions"),
]

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
    Enhance the user's query with targeted domain keywords.
    Uses fast deterministic matching only (<0.1ms, 0 tokens).

    When no heuristic pattern matches, the original query is returned
    unchanged — the dense vector retriever handles semantic matching.
    """
    q_clean = query.strip()
    if not q_clean:
        return query

    # Fast deterministic keyword expansion (0ms, 0 tokens)
    matched_expansions = []
    for pattern, expansion in FAST_KEYWORD_EXPANSIONS:
        if pattern.search(q_clean):
            matched_expansions.append(expansion)

    if matched_expansions:
        # Combine unique keywords from matched expansions
        combined = " ".join(matched_expansions)
        words = list(dict.fromkeys(combined.split()))
        return " ".join(words[:10])

    # No match — return original query (dense retriever handles semantics)
    return q_clean