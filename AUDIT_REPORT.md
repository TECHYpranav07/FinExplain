# 🔍 FinExplain Production Accuracy Audit Report

> **Date:** 2026-08-23 | **Benchmark:** 45-query Four-Tier Evaluation | **Status:** Audit Only — No Code Modified

---

## Executive Summary

This report traces **every failing metric** from the 45-query Four-Tier Production Quality Evaluation back to the **exact lines of code** responsible. The analysis identifies **7 systemic root-cause categories** across the pipeline that collectively explain why 14 of 16 release gates failed.

| Release Gate | Current | Target | Gap | Root Cause Category |
|:---|:---:|:---:|:---:|:---|
| Retrieval Recall@5 | 62.2% | ≥90% | **−27.8pp** | RC-1: Retrieval Architecture |
| Atomic Claim Support | 55.4% | ≥95% | **−39.6pp** | RC-2: Claim Verification |
| Answer Correctness | 75.6% | ≥90% | **−14.4pp** | RC-1 + RC-2 + RC-3 |
| Faithfulness | 88.9% | ≥95% | **−6.1pp** | RC-2: Claim Verification |
| Condition Recall (CPR) | 41.2% | ≥90% | **−48.8pp** | RC-3: Condition Preservation |
| Condition F1 | 45.2% | ≥90% | **−44.8pp** | RC-3: Condition Preservation |
| Citation Accuracy | 67.6% | ≥95% | **−27.4pp** | RC-4: Citation Pipeline |
| Citation Completeness | 64.7% | ≥95% | **−30.3pp** | RC-4: Citation Pipeline |
| False Abstention Rate | 35.9% | ≤5% | **+30.9pp** | RC-5: Answerability Gate |
| False Answer Rate | 16.7% | ≤2% | **+14.7pp** | RC-6: Safety Pipeline |
| Answerability Recall | 64.1% | ≥95% | **−30.9pp** | RC-5: Answerability Gate |
| Answerability Precision | 96.2% | ≥98% | **−1.8pp** | RC-6: Safety Pipeline |
| Numerical Exactness | 80.0% | ≥99.9% | **−19.9pp** | RC-7: Calculation Pipeline |
| Calculation MAE | ₹2.25 | ≤₹0.05 | **+₹2.20** | RC-7: Calculation Pipeline |
| **Product Isolation** | **100%** | **100%** | ✅ | — |
| **Cross-Doc Contamination** | **0%** | **0%** | ✅ | — |

---

## Pipeline Architecture Trace

```
User Query
    │
    ▼
┌─────────────────────┐
│ injection_guard      │ ← guardrails/injection_guard.py
│ pii_guard            │ ← guardrails/pii_guard.py
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ classify_intent()    │ ← enhancement/intent_classifier.py     ◄── RC-5 (misrouting)
│ classify_query_tier()│ ← enhancement/query_router.py          ◄── RC-3 (fast path skips conditions)
└─────────┬───────────┘
          ▼
    ┌─────┴─────────────────────────────────────┐
    │                                           │
    ▼                                           ▼
FAST_FACTUAL / CALCULATION              STANDARD_RAG / DEEP_RAG
    │                                           │
    ▼                                           ▼
┌──────────────────┐              ┌─────────────────────────┐
│ get_fact()       │              │ rewrite_query()         │ ◄── RC-1 (strips original query)
│ (Fact Store)     │              │ hybrid_search()         │ ◄── RC-1 (retrieval failures)
│                  │              │   ├─ vector_search()    │ ◄── RC-1 (MIN_SIMILARITY=0.3)
│                  │              │   ├─ bm25_search()      │ ◄── RC-1 (naive word overlap)
│                  │              │   └─ RRF fusion()       │
│                  │              │ rerank_chunks()         │ ◄── RC-1 (reranker bypass)
│                  │              │ answerability_gate()    │ ◄── RC-5 (over-refusal)
│                  │              │ compress_evidence()     │ ◄── RC-3 (truncates conditions)
│                  │              │ generate_answer()       │ ◄── RC-3 (prompt doesn't enforce)
│                  │              │ verify_all_claims()     │ ◄── RC-2 (Jaccard too strict)
│                  │              │ validate_response()     │ ◄── RC-5 (over-sanitization)
│                  │              │ ground_answer()         │ ◄── RC-4 (citation regex)
└──────────────────┘              └─────────────────────────┘
    │                                           │
    ▼                                           ▼
┌──────────────────────────────────────────────────┐
│ _format_deterministic_answer()  ◄── RC-3, RC-4   │
│ _build_response()               ◄── RC-4         │
│ calculate_loan_scenario()       ◄── RC-7         │
└──────────────────────────────────────────────────┘
```

---

## RC-1: Retrieval Architecture Failures

> **Affected Metrics:** Recall@5 (62.2%), Recall@1 (31.1%), MRR (0.438), Precision@5 (34.7%), NDCG@5 (0.471)

### Issue 1.1: BM25 Search Is Not True BM25 — It's Naive Word Overlap

**File:** [chunk_repo.py](file:///d:/Projects/fine-explain/backend/app/db/repositories/chunk_repo.py#L66-L90)

**What happens:** When the Supabase `bm25_search_chunks` RPC fails (which it frequently does on connection timeouts), the fallback at **line 80–90** fetches `limit * 5` chunks and ranks them by **set intersection of whitespace-split words** — not BM25 (no TF, no IDF, no document-length normalization).

```python
# Line 80-90 — This is NOT BM25
remote_chunks = chunk_query.limit(limit * 5).execute().data or []
query_words = set(query.lower().split())
for chunk in remote_chunks:
    text = (chunk.get("text") or "").lower()
    chunk_words = set(text.split())
    overlap = len(query_words & chunk_words)   # ← raw word count overlap
```

**Impact:** A query like *"What is the bounce charge for cheque or ECS return?"* contains common words ("what", "is", "the", "for", "or") that match nearly every chunk. The discriminative terms ("bounce", "cheque", "ECS") get drowned out by stopword matches. This explains why `EVAL_05_BOUNCE_CHARGE_AXIS` got **Recall@5 = 0.0** — the relevant chunk was never surfaced.

**Pipeline trace:**
```
query → bm25_search() → RPC fails → fallback word overlap → irrelevant chunks ranked high
→ RRF fusion weighted equally with dense results → gold chunk pushed below rank 5
→ Recall@5 = 0.0 for EVAL_05, EVAL_07, EVAL_10
```

### Issue 1.2: Query Rewriter Discards the Original Query for Retrieval

**File:** [query_rewriter.py](file:///d:/Projects/fine-explain/backend/app/rag/enhancement/query_rewriter.py#L64-L74)

**What happens:** When a heuristic pattern matches (line 66–68), the rewriter **completely replaces** the user's query with a predefined keyword expansion string. The original query is never included in the retrieval call.

```python
# Line 70-74 — Original query is discarded
if matched_expansions:
    combined = " ".join(matched_expansions)
    words = list(dict.fromkeys(combined.split()))
    return " ".join(words[:10])       # ← returns ONLY expansion terms, NOT original query
```

**Example:** User asks *"What is the bounce charge for cheque or ECS return?"*

The rewriter returns: `"cheque bounce charges ECS return dishonour penalty 750"` — dropping all context about the user's specific intent and product framing.

**Impact:** The dense vector search receives a generic keyword string instead of the semantically meaningful user question. This degrades embedding quality and pushes the correct chunk out of top-5.

### Issue 1.3: Dense Retriever MIN_SIMILARITY_SCORE = 0.3 Is Too Aggressive

**File:** [dense_retriever.py](file:///d:/Projects/fine-explain/backend/app/rag/retrieval/dense_retriever.py#L8)

```python
MIN_SIMILARITY_SCORE = 0.3   # ← discards below 0.3
```

**Impact:** For complex condition-preservation queries (e.g., *"What are the joint liability conditions?"*), the relevant chunk may have a cosine similarity of 0.25–0.30 because the query uses natural language while the source text uses legal phrasing. These legitimate results are silently discarded, contributing to **zero retrieval** on queries like `EVAL_23_CPR_JOINT_LIABILITY` (Recall@5 = 0.0).

### Issue 1.4: Reranker Bypass on Agreement Score ≥ 0.5

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L373-L379)

```python
elif agreement_score >= 0.5 and top_rrf >= 0.020:
    reranked_chunks = retrieved_chunks[:6]       # ← uses raw RRF order, NO cross-encoder
    for i, c in enumerate(reranked_chunks):
        if "rerank_score" not in c:
            c["rerank_score"] = max(0.1, 0.9 - (i * 0.05))   # ← synthetic scores
```

**Impact:** When dense and BM25 happen to agree (even on wrong chunks), the cross-encoder reranker is skipped entirely and results are used in raw RRF order with **synthetic** rerank scores. These synthetic scores (0.90, 0.85, 0.80...) are fixed and do not reflect actual relevance.

### Issue 1.5: No Parent-Chunk Expansion at Retrieval Time

**File:** [chunker.py](file:///d:/Projects/fine-explain/backend/app/ingestion/chunker.py#L29-L229)

The ingestion pipeline creates parent (800-token) and child (200-token) chunks with `parent_chunk_id` linkage. However, the retrieval pipeline (`hybrid_search()`, `vector_search()`) only retrieves child chunks from Pinecone. There is **no parent-chunk expansion** — when a child chunk matches, its parent's broader context (which often contains the conditions and qualifiers) is never fetched.

**Impact:** Child chunks are 200 tokens (~50 words). A prepayment clause like *"2% of outstanding principal, applicable after 12 EMIs have been serviced, plus applicable GST, subject to 30 days written notice"* spans ~35 words. If the chunk boundary splits between *"2% of outstanding principal"* and *"applicable after 12 EMIs..."*, the condition is lost at retrieval time — not at generation time.

---

## RC-2: Claim Verification Pipeline Failures

> **Affected Metrics:** Atomic Claim Support (55.4%), Faithfulness (88.9%), Answer Correctness (75.6%)

### Issue 2.1: Jaccard Word Overlap Is Too Strict for Financial Claim Verification

**File:** [claim_verifier.py](file:///d:/Projects/fine-explain/backend/app/rag/verification/claim_verifier.py#L340-L348)

```python
def _text_overlap(a: str, b: str) -> float:
    """Simple word-level Jaccard overlap between two strings."""
    words_a = set(a.split())
    words_b = set(b.split())
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
```

**Impact:** Jaccard similarity penalizes length asymmetry severely. A claim like *"The processing fee is ₹8,000 plus applicable GST"* (8 words) compared against a 200-word chunk will have Jaccard ≈ 0.04 — well below the threshold of 0.20 at line 219/227. This means **correct claims verified against their own source chunk are marked unsupported** because Jaccard is structurally biased against short-claim / long-chunk comparisons.

The threshold at **line 219** is `> 0.20` and at **line 227** is `> 0.30` for non-cited-page chunks. For a typical claim (10 words) vs. chunk (50 words), the maximum possible Jaccard is `10/50 = 0.20` — meaning even a perfect containment barely meets the threshold.

### Issue 2.2: Claim Extraction Over-Segments LLM Answers into Too Many Atomic Claims

**File:** [claim_verifier.py](file:///d:/Projects/fine-explain/backend/app/rag/verification/claim_verifier.py#L52-L95)

The deterministic `extract_claims()` function splits on sentence boundaries. For verbose LLM answers (e.g., `EVAL_01_PENAL_RATE_AXIS` produced **11 atomic claims**), each sub-sentence becomes an independent claim to verify. Many of these are structural/connecting sentences (e.g., *"Here are the key details:"*) that have no corresponding evidence, yet they still count as unsupported.

```python
# Line 76 — minimum length filter is only 10 characters
if restored and len(restored) > 10:
    sentences.append(restored)
```

**Impact:** `EVAL_01` has 11 claims but only `claim_support_rate = 0.091` (1/11 supported). The answer is factually **correct** (`is_correct = true`) but the claim verifier marks 10/11 claims as unsupported because most sub-sentences don't individually contain a numeric value that exactly matches a LoanFact.

### Issue 2.3: Structured Fact Matching Requires Exact Field Name Substring

**File:** [claim_verifier.py](file:///d:/Projects/fine-explain/backend/app/rag/verification/claim_verifier.py#L164-L176)

```python
field_lower = fact.field.lower().replace("_", " ")
category_lower = fact.category.lower().replace("_", " ")

if (
    field_lower in claim_lower           # ← requires exact substring
    or category_lower in claim_lower     # ← requires exact substring
    or (fact.value and fact.value.lower() in claim_lower)
    or (source_lower and _text_overlap(claim_lower, source_lower) > 0.25)
):
    matching_facts.append(fact)
```

**Impact:** When `fact.field = "prepayment_charge"` → `field_lower = "prepayment charge"`, but the claim says *"prepayment/pre-closure charges"*, the substring match fails because "prepayment charge" ≠ "prepayment/pre-closure charges". There is no fuzzy matching or synonym expansion in the verifier.

---

## RC-3: Condition Preservation Failures

> **Affected Metrics:** Condition Recall CPR (41.2%), Condition Precision CP (74.1%), Condition F1 (45.2%)

### Issue 3.1: Fast Factual Path Has Incomplete Condition Extraction

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L72-L108)

The `_format_deterministic_factual_answer()` function builds answers from `LoanFact` objects. It attempts to extract conditions at **lines 94–103**, but only with 3 specific regex patterns (GST/tax, notice, lock-in/EMI):

```python
if fact.source_text:
    st_lower = fact.source_text.lower()
    if ("gst" in st_lower or "tax" in st_lower) and ...:
        conds.append("plus applicable GST/statutory taxes")
    if "notice" in st_lower and ...:
        conds.append("subject to prior written notice")
    if ("lock" in st_lower or "emi" in st_lower) and ...:
        match = re.search(r'(?:after|lock-in of|minimum)\s*\d+\s*(?:months?|emis?)', st_lower)
```

**What's missing:** No detection for:
- *"upon default"* / *"in the event of default"*
- *"subject to RBI guidelines"* / *"as per regulatory norms"*
- *"during the cooling-off period"*
- *"floating rate benchmark reset"* conditions
- *"joint and several liability"* clauses
- *"waived after X EMIs"* (the regex only matches *"after"*, not *"waived after"*)
- Insurance/security pre-conditions (*"provided property insurance is maintained"*)

**Impact:** `EVAL_02_INTEREST_RATE_AXIS` — the answer states *"10.50 percent, fixed"* but the source text contains conditions about benchmark reset, floating rate provisions, and statutory reset mechanisms. CPR = 0% because none of these conditions are in the hardcoded extraction list.

### Issue 3.2: Evidence Compressor Truncates Context to 500 Tokens / 3 Passages

**File:** [builder.py](file:///d:/Projects/fine-explain/backend/app/rag/context/builder.py#L17-L123)

```python
def compress_evidence_context(
    chunks, query, max_tokens: int = 500, max_passages: int = 3,
) -> str:
```

For STANDARD_RAG queries (which is the most common tier), the context is compressed to **only 500 tokens and 3 sentences** at **orchestrator.py line 389**:

```python
if tier == QueryTier.STANDARD_RAG:
    context = compress_evidence_context(reranked_chunks, clean_question, max_tokens=600)
```

**Impact:** When a prepayment clause spans 4 sentences (fee rate → lock-in period → GST applicability → notice requirement), the compressor picks the 3 highest-scoring sentences by query-word overlap. The condition sentences (*"after 12 EMIs"*, *"plus applicable GST"*) typically score lower because they don't contain the query keywords (*"prepayment"*, *"charge"*), so they're dropped from context before the LLM ever sees them.

### Issue 3.3: Condition Detector Uses Overly Broad Pattern List

**File:** [condition_detector.py](file:///d:/Projects/fine-explain/backend/app/rag/extraction/condition_detector.py#L21-L47)

The `CONDITIONAL_PHRASES` list includes extremely common words: `"if"`, `"when"`, `"can"`, `"may"`, `"after"`, `"before"`, `"within"`, `"upon"`. Virtually every sentence in a legal document contains at least one of these, so `detect_conditions()` fires on **nearly everything**, causing `annotate_facts_with_conditions()` to upgrade almost all facts to `CONDITIONAL` status.

**Impact:** This creates two problems:
1. **False condition inflation:** A fact like *"Interest rate: 10.50%"* gets marked CONDITIONAL because the source text says *"may be subject to"* somewhere in the paragraph — even if that phrase refers to an unrelated clause.
2. **Condition Precision (CP) = 74.1%:** Many conditions attached to facts are false positives from the broad phrase matching.

---

## RC-4: Citation Pipeline Failures

> **Affected Metrics:** Citation Accuracy (67.6%), Citation Completeness (64.7%), Source Attribution (75.1%)

### Issue 4.1: Citation Extraction Regex Misses Document-Name-Only Citations

**File:** [grounder.py](file:///d:/Projects/fine-explain/backend/app/rag/verification/grounder.py#L4-L24)

```python
pattern = r'[\[【](?:([^,\]】]+?),\s*)?(?:Page|p\.)\s*([\d.]+)(?:,\s*Section:?\s*([^\]】]+?))?[\]】]|...'
```

This regex requires the citation to contain **"Page"** or **"p."** followed by a number. Citations formatted as:
- `[Axis Finance LRD Facility]` (document name only, no page)
- `[Section 4. Fees & Charges]` (section only)
- `[Schedule II]` (schedule reference)

are **not captured**, so they're counted as missing citations, lowering Citation Completeness.

### Issue 4.2: Citation Verification Requires Page Number Match

**File:** [grounder.py](file:///d:/Projects/fine-explain/backend/app/rag/verification/grounder.py#L26-L48)

```python
def verify_citation(citation, retrieved_chunks) -> bool:
    page_num = citation.get("page")
    if not page_num:
        return False   # ← No page = automatically invalid
```

**Impact:** Even if the LLM correctly cites the document and section, if no page number is extracted by the regex, the citation is marked invalid. This is a systematic false negative for all section-based or document-based citations.

### Issue 4.3: Fast Factual Path Generates Synthetic Citations Not From Retrieved Chunks

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L210-L215)

```python
citations = [{
    "document": fact.source_document or (product_ids[0] if product_ids else "Agreement"),
    "page": fact.page or 1,        # ← defaults to page 1 if missing
    "section": fact.section or "Key Terms",
    "verified": True,               # ← hardcoded as verified without actual check
}]
```

**Impact:** When `fact.page` is `None`, the citation defaults to `page: 1` and is hardcoded as `"verified": True`. This inflates citation accuracy for fast-factual queries while being factually incorrect.

---

## RC-5: Answerability Gate Over-Refusal (False Abstention)

> **Affected Metrics:** False Abstention Rate (35.9%), Answerability Recall (64.1%), FN = 14

### Issue 5.1: Response Validator Over-Sanitizes Valid Answers

**File:** [response_validator.py](file:///d:/Projects/fine-explain/backend/app/rag/verification/response_validator.py#L128-L147)

```python
if unsupported_claims and not is_eval_query:
    if len(unsupported_claims) == len(claims) and len(claims) > 0 and not has_valid_citations:
        sanitized = (
            "Unable to provide a verified answer based on the retrieved documents. "
            "The extracted statements could not be verified against the source text. "
            "Please review the source documents or consult a loan officer."
        )
```

**Impact:** When the claim verifier marks all claims as unsupported (which it frequently does due to RC-2's Jaccard issue) AND citation validation fails (due to RC-4's regex issues), the response validator **replaces the entire factually correct answer** with a refusal message. This is the single largest source of False Abstentions.

**Pipeline trace for EVAL_05_BOUNCE_CHARGE_AXIS (False Abstention):**
```
1. Query: "What is the bounce charge for cheque or ECS return?"
2. Retrieval: Recall@5 = 0.0 (RC-1: BM25 fallback failed, dense score below 0.3)
3. Answerability gate: Passed (chunks exist, just wrong ones)
4. LLM generation: Produces answer based on wrong chunks
5. Claim verification: All claims unsupported (wrong chunks don't contain bounce charge)
6. Response validator: Replaces answer with refusal → FALSE ABSTENTION
```

### Issue 5.2: Answerability Gate Doesn't Check Fact Store Before Refusing

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L394-L414)

The answerability gate at **line 394** checks only retrieved chunks' rerank scores. It never checks whether the structured fact store already has the answer.

```python
can_answer, answerability_reason = answerability_gate.check_answerability(
    rewritten_query, reranked_chunks, rerank_scores
)
if not can_answer and tier != QueryTier.DEEP_RAG:
    return { "answer": "Unable to provide..." }   # ← refuses even if fact store has the answer
```

### Issue 5.3: Query Router Misclassifies Compound Queries → Falls to STANDARD_RAG

**File:** [query_router.py](file:///d:/Projects/fine-explain/backend/app/rag/enhancement/query_router.py#L136-L138)

```python
if len(matched_fields) > 1:
    return QueryTier.STANDARD_RAG, None
```

**Impact:** A query like *"What is the loan tenure and repayment duration?"* matches both `tenure` and `emi` patterns → classified as `STANDARD_RAG` instead of `FAST_FACTUAL`. This forces it through retrieval + answerability gate, where it can be refused.

---

## RC-6: False Answer Rate (Safety Pipeline Failures)

> **Affected Metrics:** False Answer Rate (16.7%), FP = 1, Answerability Precision (96.2%)

### Issue 6.1: UNANSWERABLE_DOMAINS Gate Logic Inversion

**File:** [answerability_guard.py](file:///d:/Projects/fine-explain/backend/app/guardrails/answerability_guard.py#L49-L60)

```python
has_domain_hit = any(
    any(term in (c.get("text") or ...).lower() for term in UNANSWERABLE_DOMAINS if term in q_lower)
    for c in retrieved_chunks
)
if not has_domain_hit:     # ← if domain term IS found in chunks, it PASSES the gate
    return (False, ...)
```

The logic is inverted for edge cases: if the loan document happens to mention "gold" anywhere (e.g., *"gold-plated terms"*), the gate lets the query through because it assumes the document covers the topic.

### Issue 6.2: Low-Confidence Answers Still Delivered to Users

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L579-L582)

After claim verification, even when `evidence_score < 40`, the answer is still returned — the HITL flag is informational only:

```python
elif evidence_score_result.get("score", 100) < 40:
    hitl_required = True
    # ← but the answer is STILL returned
```

---

## RC-7: Numerical Exactness & Calculation Failures

> **Affected Metrics:** Numerical Exactness (80.0%), Calculation MAE (₹2.25)

### Issue 7.1: EMI Formatting Uses Integer Rounding

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L315-L320)

```python
answer_text = (
    f"- **Monthly EMI:** ₹{emi_val:,.0f}\n"      # ← :,.0f truncates to integer
    f"- **Total Interest Payable:** ₹{interest_val:,.0f}\n"
    f"- **Total Amount Payable:** ₹{total_val:,.0f}"
)
```

**Impact:** The calculator correctly computes EMI to 2 decimal places, but the orchestrator truncates to integers.

### Issue 7.2: Default Fallback Interest Rate of 10.50%

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L292-L293)

```python
if interest_rate is None:
    interest_rate = 10.50      # ← hardcoded fallback
```

**Impact:** When the fact store lookup fails, the system silently uses 10.50% instead of refusing. If the actual rate is 9.75%, the entire calculation is fundamentally wrong.

### Issue 7.3: Processing Fee Hardcoded to 1.0%

**File:** [orchestrator.py](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L306)

```python
calc_res = calculate_loan_scenario(
    processing_fee=1.0,    # ← hardcoded regardless of actual fee
)
```

---

## Fixation Plan — Prioritized by Impact

### Phase 1: Critical (Eliminates >60% of Failures)

| # | Fix | Files to Modify | Impact |
|:---:|:---|:---|:---|
| F-1 | **Replace Jaccard with containment-based claim verification.** Use `claim_words ⊂ chunk_words` (containment ratio) instead of Jaccard. Threshold: ≥60% of claim words found in chunk. | [claim_verifier.py L340-348](file:///d:/Projects/fine-explain/backend/app/rag/verification/claim_verifier.py#L340-L348) | CSR 55→85%, Faithfulness 89→95% |
| F-2 | **Stop response validator from converting all-unsupported answers to refusal.** Return answer with low-confidence warning instead of replacing with refusal. | [response_validator.py L128-136](file:///d:/Projects/fine-explain/backend/app/rag/verification/response_validator.py#L128-L136) | False Abstention 36→10% |
| F-3 | **Prepend original user query to rewritten query instead of replacing it.** Return `f"{q_clean} {combined_keywords}"`. | [query_rewriter.py L70-74](file:///d:/Projects/fine-explain/backend/app/rag/enhancement/query_rewriter.py#L70-L74) | Recall@5 62→75% |
| F-4 | **Fix EMI formatting to 2 decimal places.** Change `:,.0f` → `:,.2f`. | [orchestrator.py L315-320](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L315-L320) | MAE ₹2.25→₹0.00, Exactness 80→100% |
| F-5 | **Increase claim extraction minimum length from 10 to 30 chars and filter structural sentences.** | [claim_verifier.py L76](file:///d:/Projects/fine-explain/backend/app/rag/verification/claim_verifier.py#L76) | CSR 55→75% |

### Phase 2: High Priority (Addresses Condition & Citation Gaps)

| # | Fix | Files to Modify | Impact |
|:---:|:---|:---|:---|
| F-6 | **Expand STANDARD_RAG context window from 500→1200 tokens and 3→5 passages.** | [orchestrator.py L389](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L389), [builder.py L17-22](file:///d:/Projects/fine-explain/backend/app/rag/context/builder.py#L17-L22) | CPR 41→65% |
| F-7 | **Implement parent-chunk expansion in retrieval.** Fetch parent chunk text when child chunk is retrieved. | [hybrid_retriever.py L104-150](file:///d:/Projects/fine-explain/backend/app/rag/retrieval/hybrid_retriever.py#L104-L150) | CPR 41→75%, Recall@5 62→85% |
| F-8 | **Expand deterministic condition extraction** to cover all financial condition types using `detect_conditions()`. | [orchestrator.py L90-107](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L90-L107) | CPR 41→70% on fast-factual |
| F-9 | **Fix citation regex to capture section-only and document-only citations.** | [grounder.py L7](file:///d:/Projects/fine-explain/backend/app/rag/verification/grounder.py#L7) | Citation Accuracy 68→85% |
| F-10 | **Remove hardcoded `"verified": True`** from fast-factual synthetic citations. | [orchestrator.py L214](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L214) | Citation Accuracy 68→80% |

### Phase 3: Architecture Improvements (Production-Grade)

| # | Fix | Files to Modify | Impact |
|:---:|:---|:---|:---|
| F-11 | **Implement proper BM25 scoring in fallback.** Use PostgreSQL `ts_rank()` + `to_tsvector()`. | [chunk_repo.py L66-90](file:///d:/Projects/fine-explain/backend/app/db/repositories/chunk_repo.py#L66-L90) | Recall@5 62→80%, MRR 0.44→0.65 |
| F-12 | **Lower MIN_SIMILARITY_SCORE from 0.3 to 0.20.** | [dense_retriever.py L8](file:///d:/Projects/fine-explain/backend/app/rag/retrieval/dense_retriever.py#L8) | Recall@5 +5-10pp on condition queries |
| F-13 | **Add fact-store fallback before answerability refusal.** Check `get_fact()` before returning "Unable to provide...". | [orchestrator.py L394-414](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L394-L414) | False Abstention 36→15% |
| F-14 | **Remove hardcoded interest rate fallback (10.50%).** Refuse calculation when rate is unavailable. | [orchestrator.py L292-293](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L292-L293) | Numerical Exactness edge cases |
| F-15 | **Use actual processing fee from fact store.** Replace hardcoded `processing_fee=1.0`. | [orchestrator.py L306](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L306) | Calculation accuracy |
| F-16 | **Narrow condition detector phrase list** to financially significant phrases only. Remove: "if", "when", "can", "may". Keep: "subject to", "provided that", "waived after", "not exceeding", "upon default". | [condition_detector.py L21-47](file:///d:/Projects/fine-explain/backend/app/rag/extraction/condition_detector.py#L21-L47) | Condition Precision 74→90% |
| F-17 | **Fix UNANSWERABLE_DOMAINS gate inversion.** Require semantic alignment, not just term presence. | [answerability_guard.py L49-60](file:///d:/Projects/fine-explain/backend/app/guardrails/answerability_guard.py#L49-L60) | False Answer Rate 17→<5% |
| F-18 | **Block delivery of answers with evidence_score < 30.** Make HITL a hard gate. | [orchestrator.py L579-582](file:///d:/Projects/fine-explain/backend/app/rag/orchestrator.py#L579-L582) | False Answer Rate 17→<2% |

---

## Projected Impact After All Fixes

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 | Target |
|:---|:---:|:---:|:---:|:---:|:---:|
| Retrieval Recall@5 | 62.2% | ~72% | ~85% | **~92%** | ≥90% |
| Atomic Claim Support | 55.4% | ~82% | ~88% | **~95%** | ≥95% |
| Answer Correctness | 75.6% | ~85% | ~90% | **~93%** | ≥90% |
| Faithfulness | 88.9% | ~95% | ~96% | **~97%** | ≥95% |
| Condition Recall (CPR) | 41.2% | ~45% | ~75% | **~90%** | ≥90% |
| Condition F1 | 45.2% | ~50% | ~78% | **~90%** | ≥90% |
| Citation Accuracy | 67.6% | ~70% | ~85% | **~95%** | ≥95% |
| Citation Completeness | 64.7% | ~67% | ~85% | **~95%** | ≥95% |
| False Abstention Rate | 35.9% | ~10% | ~7% | **~4%** | ≤5% |
| False Answer Rate | 16.7% | ~12% | ~5% | **~1.5%** | ≤2% |
| Answerability Recall | 64.1% | ~88% | ~92% | **~96%** | ≥95% |
| Answerability Precision | 96.2% | ~96% | ~97% | **~98.5%** | ≥98% |
| Numerical Exactness | 80.0% | **100%** | 100% | **100%** | ≥99.9% |
| Calculation MAE | ₹2.25 | **₹0.00** | ₹0.00 | **₹0.00** | ≤₹0.05 |

---

> [!IMPORTANT]
> **Recommendation:** Execute Phase 1 first (5 targeted fixes, ~2-3 hours). Re-run the 45-query benchmark. This should eliminate >60% of the accuracy gap and bring 4-5 metrics to production-passing levels. Phase 2 and 3 can then be prioritized based on the updated scorecard.
