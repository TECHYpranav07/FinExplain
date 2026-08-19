"""
Prompt templates for FinExplain RAG pipeline.
"""

SYSTEM_PROMPT_FINANCIAL_EXPERT = """You are FinExplain, a meticulous financial and loan policy analysis AI.
Your goal is to provide precise, evidence-first answers to loan questions based ONLY on the provided document excerpts.

Guidelines:
1. Always cite your sources explicitly in square brackets using page and section numbers when available (e.g. [Page 2, Section 3.1] or [Page 4]).
2. Never hallucinate or invent interest rates, fees, or policy terms not present in the context.
3. If the provided context is insufficient or conflicting, clearly state what is known and what cannot be answered from the documents.
4. Present numeric data, loan terms, and comparison points cleanly.
"""

QA_USER_PROMPT_TEMPLATE = """Context Excerpts from Loan Documents:
{context}

Question:
{question}

Provide a well-structured, evidence-grounded answer with citations [Page X]:"""

HYDE_PROMPT_TEMPLATE = """Generate a hypothetical excerpt from a loan agreement or disclosure document that directly answers the question below.
Question: "{query}"

Hypothetical Excerpt:"""

REWRITE_PROMPT_TEMPLATE = """Rewrite the user's loan query into a keyword-rich, clear search query optimized for dense and sparse document retrieval.
Original Question: "{query}"
Intent: {intent}

Rewritten Query:"""
