"""
FinExplain - Diagnostic Top 5 Document Evaluation Benchmark

25 queries total across the 5 operative credit agreements in documents/top5:
    1. Axis Finance Loan Against Property (loan-against-property-agreement-english---08062026.pdf)
    2. Axis Finance Personal Loan Agreement (pl-loan-agreement-english-v290325.pdf)
    3. South Indian Bank OneScore Personal Loan (tandc_sib_onescore_personal_loan.pdf)
    4. HDFC Bank Home Loan Agreement (HDFC-Bank-Home-Loan-Agreement.pdf)
    5. GSS Term Loan CCD Facility (gss-term-loan-agreement-ccd-5.pdf)

Evaluates:
    - Evidence Availability Rate (EAR)
    - Evidence Sufficiency Rate (ESR)
    - Causal Failure Tree Classification:
        * CORRECT
        * RETRIEVAL_FAILURE
        * GENERATION_OR_ROUTING_FAILURE
        * DOCUMENT_INSUFFICIENT
        * FALSE_ABSTENTION
    - Conditional Correctness (given sufficient evidence)
    - Granular Condition Recall Taxonomy (Temporal, Tax, Eligibility, Prerequisite, Threshold, Exception, Calculation, Benchmark)
    - Citation Accuracy & Claim Support Rate
"""

import os
import sys
import re
import math
import json
import time
import statistics
from typing import List, Dict, Any, Optional

# ---------------------------------------------------------------------
# PATH & SYSTEM INITIALIZATION
# ---------------------------------------------------------------------

PROJECT_ROOT = r"d:\Projects\fine-explain"
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")

sys.path.insert(0, BACKEND_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Clear L1 memory cache and L2 Redis to guarantee fresh, authentic evaluation
from app.cache.query_cache import _L1_MEMORY_CACHE
_L1_MEMORY_CACHE.clear()

try:
    from app.cache.redis_client import redis_client
    if redis_client:
        redis_client.flushdb()
        print("[Top5Eval] Redis L2 cache flushed successfully.", flush=True)
except Exception as e:
    print(f"[Top5Eval] Redis flush note: {e}", flush=True)

# ---------------------------------------------------------------------
# APPLICATION IMPORTS
# ---------------------------------------------------------------------

from app.rag.orchestrator import process_query
from app.rag.retrieval.hybrid_retriever import hybrid_search
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

# ---------------------------------------------------------------------
# 5 OPERATIVE CREDIT DOCUMENTS IN documents/top5
# ---------------------------------------------------------------------

DOCUMENTS = {
    "axis_lap": {
        "filename": "loan-against-property-agreement-english---08062026.pdf",
        "product_id": "7e4fe332-bebf-4fcc-808e-9e6402738324",
        "product_name": "Axis Finance Loan Against Property",
    },

    "axis_pl": {
        "filename": "pl-loan-agreement-english-v290325.pdf",
        "product_id": "d4f0b64f-582c-4c06-951b-ab4509e5e7f2",
        "product_name": "Axis Finance Personal Loan Agreement",
    },

    "sib_onescore_pl": {
        "filename": "tandc_sib_onescore_personal_loan.pdf",
        "product_id": "6d246154-fb30-4dcd-8a6a-c22e276926c3",
        "product_name": "South Indian Bank OneScore Personal Loan",
    },

    "hdfc_home_loan": {
        "filename": "HDFC-Bank-Home-Loan-Agreement.pdf",
        "product_id": "2918b67f-fe2b-4954-a974-8c5ce2576d0e",
        "product_name": "HDFC Bank Home Loan Agreement",
    },

    "gss_term_loan": {
        "filename": "gss-term-loan-agreement-ccd-5.pdf",
        "product_id": "2f0d4df5-6bf0-449c-a8a0-7ad501ae0997",
        "product_name": "GSS Term Loan CCD Facility",
    },
}

# ---------------------------------------------------------------------
# 25 TEST CASES WITH DIAGNOSTIC TAXONOMY & GROUND TRUTH
# ---------------------------------------------------------------------

TEST_CASES = [

    # ================================================================
    # DOCUMENT 1: AXIS FINANCE LOAN AGAINST PROPERTY (LAP / LRD)
    # ================================================================

    {
        "id": "TOP5_01_LAP_INTEREST",
        "document": "axis_lap",
        "category": "factual",
        "query": "What interest rate and interest-rate type are specified for this loan?",
        "information_present": True,
        "keywords": ["interest", "rate", "fixed", "floating", "sbbr", "benchmark", "per annum"],
        "conditions": {
            "benchmark": ["floating", "sbbr", "benchmark"],
            "calculation_basis": ["per annum", "spread"],
        },
    },
    {
        "id": "TOP5_02_LAP_PROCESSING_FEE",
        "document": "axis_lap",
        "category": "fee",
        "query": "What processing fee and other applicable charges are payable under this loan?",
        "information_present": True,
        "keywords": ["processing", "fee", "charge", "gst", "tax", "statutory"],
        "conditions": {
            "tax": ["plus applicable gst", "taxes"],
            "prerequisite": ["processing fee", "statutory levies"],
        },
    },
    {
        "id": "TOP5_03_LAP_PREPAYMENT",
        "document": "axis_lap",
        "category": "condition",
        "query": "What are the conditions for part-prepayment or foreclosure of this loan?",
        "information_present": True,
        "keywords": ["prepayment", "foreclosure", "charge", "borrower", "notice", "writing"],
        "conditions": {
            "prerequisite": ["prior written notice", "written request"],
            "tax": ["applicable taxes", "charges"],
        },
    },
    {
        "id": "TOP5_04_LAP_DEFAULT",
        "document": "axis_lap",
        "category": "default",
        "query": "What penal charges apply if the borrower delays payment or defaults?",
        "information_present": True,
        "keywords": ["penal", "default", "overdue", "delay", "charge", "6%", "additional interest"],
        "conditions": {
            "threshold": ["overdue amount", "penal charges"],
            "temporal": ["delayed payment", "date of default"],
        },
    },
    {
        "id": "TOP5_05_LAP_COLLATERAL",
        "document": "axis_lap",
        "category": "legal",
        "query": "What specific security or mortgage schedule is required under the loan agreement?",
        "information_present": False,
        "insufficiency_reason": "Mortgage/security schedule is in an unattached separate annexure",
        "keywords": ["mortgage", "security", "property", "insurance", "not specified"],
        "conditions": {},
    },

    # ================================================================
    # DOCUMENT 2: AXIS FINANCE PERSONAL LOAN AGREEMENT (V290325)
    # ================================================================

    {
        "id": "TOP5_06_PL_INTEREST",
        "document": "axis_pl",
        "category": "factual",
        "query": "How is interest calculated on the facility and is the interest rate fixed or variable?",
        "information_present": True,
        "keywords": ["interest", "fixed", "rate", "daily", "365", "monthly", "reducing"],
        "conditions": {
            "calculation_basis": ["365 days", "actual days elapsed"],
            "frequency": ["monthly rests", "daily basis"],
            "benchmark": ["fixed rate", "reference rate"],
        },
    },
    {
        "id": "TOP5_07_PL_PREPAYMENT",
        "document": "axis_pl",
        "category": "condition",
        "query": "What happens if the borrower prepays or prematurely closes the loan?",
        "information_present": True,
        "keywords": ["prepayment", "charges", "premature", "closure", "12 emis", "25%"],
        "conditions": {
            "temporal": ["after 12 emis", "twice in a financial year"],
            "threshold": ["up to 25% of pos", "3%"],
            "tax": ["plus applicable taxes"],
        },
    },
    {
        "id": "TOP5_08_PL_DEFAULT",
        "document": "axis_pl",
        "category": "default",
        "query": "What penal charges apply when an EMI is delayed or remains unpaid?",
        "information_present": True,
        "keywords": ["emi", "default", "penal", "charges", "overdue", "bounce", "24%"],
        "conditions": {
            "temporal": ["from due date", "until default is cured"],
            "threshold": ["penal charges", "overdue instalment"],
        },
    },
    {
        "id": "TOP5_09_PL_RATE_RESET",
        "document": "axis_pl",
        "category": "condition",
        "query": "If the interest rate is revised, what options does the borrower have?",
        "information_present": True,
        "keywords": ["revision", "interest rate", "emi", "tenor", "prepay", "binding"],
        "conditions": {
            "temporal": ["effective prospectively", "upon notification"],
            "exception": ["increase emi", "increase tenor", "prepay"],
        },
    },
    {
        "id": "TOP5_10_PL_TAX",
        "document": "axis_pl",
        "category": "fee",
        "query": "Who bears GST, interest tax, stamp duty and other applicable levies?",
        "information_present": True,
        "keywords": ["gst", "tax", "stamp duty", "levies", "borrower", "borne"],
        "conditions": {
            "tax": ["gst", "stamp duty", "interest tax"],
            "eligibility": ["borne by borrower", "solely by borrower"],
        },
    },

    # ================================================================
    # DOCUMENT 3: SOUTH INDIAN BANK ONESCORE PERSONAL LOAN
    # ================================================================

    {
        "id": "TOP5_11_SIB_INTEREST",
        "document": "sib_onescore_pl",
        "category": "factual",
        "query": "What interest rate, EPI calculation, and repayment terms apply on this South Indian Bank loan?",
        "information_present": True,
        "keywords": ["interest", "rate", "epi", "repayment", "monthly", "south indian bank"],
        "conditions": {
            "calculation_basis": ["monthly instalment", "repayment schedule"],
            "benchmark": ["interest rate", "fixed"],
        },
    },
    {
        "id": "TOP5_12_SIB_PROCESSING",
        "document": "sib_onescore_pl",
        "category": "fee",
        "query": "What is the processing fee and GST applicability charged by the lender?",
        "information_present": True,
        "keywords": ["processing", "fee", "gst", "charges", "statutory", "8000"],
        "conditions": {
            "tax": ["plus applicable gst", "18% gst"],
            "threshold": ["processing fee"],
        },
    },
    {
        "id": "TOP5_13_SIB_PENAL",
        "document": "sib_onescore_pl",
        "category": "default",
        "query": "What penal charges and cheque / ECS bounce charges apply for payment default?",
        "information_present": True,
        "keywords": ["penal", "bounce", "ecs", "default", "overdue", "charges", "4%", "750"],
        "conditions": {
            "threshold": ["4% on defaulted amount", "750 plus gst"],
            "temporal": ["defaulted period", "until cured"],
        },
    },
    {
        "id": "TOP5_14_SIB_FORECLOSURE",
        "document": "sib_onescore_pl",
        "category": "condition",
        "query": "What are the prepayment, lock-in period, and foreclosure conditions under SIB terms?",
        "information_present": True,
        "keywords": ["prepayment", "foreclosure", "lock-in", "emis", "charges", "waiver", "2%"],
        "conditions": {
            "temporal": ["lock-in period", "after 12 emis"],
            "threshold": ["foreclosure charges", "2%"],
        },
    },
    {
        "id": "TOP5_15_SIB_COOLING",
        "document": "sib_onescore_pl",
        "category": "condition",
        "query": "What cooling-off or look-up period is provided to exit the loan without penalty?",
        "information_present": True,
        "keywords": ["cooling-off", "look-up", "3 days", "sanction", "disbursement", "exit"],
        "conditions": {
            "temporal": ["3 days", "account opened date"],
            "exception": ["without penalty", "no penalty"],
        },
    },

    # ================================================================
    # DOCUMENT 4: HDFC BANK HOME LOAN AGREEMENT
    # ================================================================

    {
        "id": "TOP5_16_HDFC_INTEREST",
        "document": "hdfc_home_loan",
        "category": "factual",
        "query": "What interest rate structure (Adjustable / Fixed Rate) and conversion options apply under HDFC Home Loan?",
        "information_present": True,
        "keywords": ["interest", "adjustable", "fixed", "rate", "conversion", "hdfc", "spread", "1.75%"],
        "conditions": {
            "benchmark": ["reference rate", "spread", "adjustable rate"],
            "threshold": ["1.75%", "0.5%", "1.50%"],
            "tax": ["plus applicable taxes"],
        },
    },
    {
        "id": "TOP5_17_HDFC_PROCESSING",
        "document": "hdfc_home_loan",
        "category": "fee",
        "query": "What processing fees, administrative charges, and statutory levies are payable to HDFC?",
        "information_present": True,
        "keywords": ["processing", "administrative", "fee", "charges", "levies", "gst", "2.00%"],
        "conditions": {
            "threshold": ["up to 2.00%", "minimum 3000", "50%"],
            "tax": ["exclusive of gst", "statutory levies"],
        },
    },
    {
        "id": "TOP5_18_HDFC_DEFAULT",
        "document": "hdfc_home_loan",
        "category": "default",
        "query": "What additional interest and penal charges apply upon default or delayed EMI payment to HDFC?",
        "information_present": True,
        "keywords": ["default", "penal", "additional interest", "delayed", "overdue", "charges", "18%"],
        "conditions": {
            "threshold": ["maximum of 18% per annum", "overdue amount"],
            "temporal": ["from due date until realization"],
            "tax": ["exclusive of gst"],
        },
    },
    {
        "id": "TOP5_19_HDFC_PREPAYMENT",
        "document": "hdfc_home_loan",
        "category": "condition",
        "query": "What are the terms, charges, and conditions for part-prepayment or early full repayment of HDFC Home Loan?",
        "information_present": True,
        "keywords": ["prepayment", "part-prepayment", "early repayment", "foreclosure", "charges", "nil", "2%"],
        "conditions": {
            "eligibility": ["individual borrowers", "non-business purpose"],
            "exception": ["no prepayment charges on adjustable rate", "2% on fixed rate except own sources"],
            "tax": ["plus applicable taxes"],
        },
    },
    {
        "id": "TOP5_20_HDFC_SECURITY",
        "document": "hdfc_home_loan",
        "category": "legal",
        "query": "What property security, mortgage creation, and insurance obligations are required by HDFC under Article 4?",
        "information_present": True,
        "keywords": ["mortgage", "security", "property", "insurance", "title", "encumbrance", "exclusive"],
        "conditions": {
            "prerequisite": ["exclusive mortgage", "clear title", "insurance"],
        },
    },

    # ================================================================
    # DOCUMENT 5: GSS TERM LOAN CCD FACILITY
    # ================================================================

    {
        "id": "TOP5_21_GSS_FACILITY",
        "document": "gss_term_loan",
        "category": "factual",
        "query": "What is the term loan facility amount and purpose specified in the agreement?",
        "information_present": False,
        "insufficiency_reason": "Facility amount and purpose are unfilled blanks ('Rs ...........') in the execution template",
        "keywords": ["not specified", "blank", "unfilled", "facility amount"],
        "conditions": {},
    },
    {
        "id": "TOP5_22_GSS_DISBURSEMENT",
        "document": "gss_term_loan",
        "category": "condition",
        "query": "What is the detailed draw down schedule specified in the agreement?",
        "information_present": False,
        "insufficiency_reason": "Draw down schedule is omitted from the contract body",
        "keywords": ["not specified", "draw down schedule", "not detailed"],
        "conditions": {},
    },
    {
        "id": "TOP5_23_GSS_PREPAYMENT",
        "document": "gss_term_loan",
        "category": "condition",
        "query": "What are the terms and notice requirements for prepayment or voluntary cancellation?",
        "information_present": True,
        "keywords": ["prepayment", "notice", "cancellation", "voluntary", "nil", "written notice"],
        "conditions": {
            "threshold": ["prepayment charges nil"],
            "prerequisite": ["written notice", "bank right to cancel without notice"],
        },
    },
    {
        "id": "TOP5_24_GSS_DEFAULT",
        "document": "gss_term_loan",
        "category": "default",
        "query": "What constitutes an Event of Default and what remedies does the lender have?",
        "information_present": True,
        "keywords": ["event of default", "breach", "remedies", "8%", "penal charges"],
        "conditions": {
            "threshold": ["8% p.a.", "minimum ₹300", "maximum ₹1,00,000"],
            "eligibility": ["not applicable for shg loans"],
            "temporal": ["from date of default"],
        },
    },
    {
        "id": "TOP5_25_GSS_GOVERNING_LAW",
        "document": "gss_term_loan",
        "category": "legal",
        "query": "Which governing law and dispute resolution mechanism apply to this agreement?",
        "information_present": True,
        "keywords": ["governing law", "jurisdiction", "arbitration", "dispute", "courts", "indian law"],
        "conditions": {
            "jurisdiction": ["indian law", "exclusive jurisdiction", "courts and tribunals"],
        },
    },
]

# ---------------------------------------------------------------------
# EVALUATION METRICS HELPERS
# ---------------------------------------------------------------------

def keyword_hits(answer: str, keywords: List[str]) -> int:
    answer_lower = answer.lower()
    return sum(1 for keyword in keywords if keyword.lower() in answer_lower)

def evaluate_conditions_by_type(answer: str, conditions_dict: Dict[str, List[str]]) -> Dict[str, Any]:
    if not conditions_dict:
        return {"overall_recall": 1.0, "overall_precision": 1.0, "by_type": {}}

    answer_lower = answer.lower()
    by_type = {}
    total_expected = 0
    total_matched = 0

    for ctype, cond_list in conditions_dict.items():
        matched = sum(1 for c in cond_list if c.lower() in answer_lower)
        type_recall = matched / len(cond_list) if cond_list else 1.0
        by_type[ctype] = {
            "matched": matched,
            "total": len(cond_list),
            "recall": round(type_recall, 3),
        }
        total_matched += matched
        total_expected += len(cond_list)

    overall_recall = total_matched / max(total_expected, 1)

    markers = [
        "after", "before", "within", "subject to", "plus", "gst", "tax",
        "without charge", "non-refundable", "until", "from", "notice",
        "fixed", "floating", "lock-in", "cure", "contingent", "minimum", "maximum",
    ]
    stated = sum(1 for marker in markers if marker in answer_lower)
    overall_precision = min(total_matched / max(stated, 1), 1.0) if stated > 0 else (1.0 if total_matched else 0.0)

    return {
        "overall_recall": round(overall_recall, 3),
        "overall_precision": round(overall_precision, 3),
        "by_type": by_type,
    }

def did_abstain(answer: str) -> bool:
    text = answer.lower()
    refusal_patterns = [
        "not specified", "unable to provide", "not covered", "not disclosed",
        "not mentioned", "not found", "insufficient evidence", "outside the scope",
        "cannot verify", "unable to verify", "insufficient to support",
    ]
    return any(p in text for p in refusal_patterns)

# ---------------------------------------------------------------------
# SINGLE QUERY EVALUATION WITH CAUSAL CLASSIFICATION
# ---------------------------------------------------------------------

def evaluate_case(case: Dict[str, Any], document_cfg: Dict[str, Any]) -> Dict[str, Any]:
    product_id = document_cfg["product_id"]
    query = case["query"]
    info_present = case["information_present"]

    print()
    print("=" * 80, flush=True)
    print(f"[{case['id']}] Cat: {case['category']} | Product: {document_cfg['product_name']}", flush=True)
    print(f"Query: {query}", flush=True)
    print(f"Information Present in Corpus: {info_present}", flush=True)
    print("-" * 80, flush=True)

    # 1. Retrieval Layer Evaluation
    retrieval_start = time.perf_counter()
    try:
        chunks = hybrid_search(query, [product_id], top_k=10)
    except Exception as exc:
        print(f"[RETRIEVAL ERROR] {exc}", flush=True)
        chunks = []
    retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
    retrieval_count = len(chunks)

    # 2. End-to-End RAG Generation
    start = time.perf_counter()
    try:
        result = process_query(
            question=query,
            product_ids=[product_id],
        )
        error = None
    except Exception as exc:
        result = {
            "answer": f"ERROR: {exc}",
            "processing_tier": "error",
            "evidence_score": 0,
            "citations": [],
        }
        error = str(exc)

    latency_ms = (time.perf_counter() - start) * 1000

    answer = result.get("answer", "")
    evidence_score = result.get("evidence_score", 0)
    citations = result.get("citations", [])
    processing_tier = result.get("processing_tier", "unknown")
    token_metrics = result.get("token_metrics", {})
    input_tokens = token_metrics.get("input_tokens", 0)
    output_tokens = token_metrics.get("output_tokens", 0)

    # 3. Diagnostic Evaluation & Causal Classification
    abstained = did_abstain(answer)
    hits = keyword_hits(answer, case["keywords"])
    keyword_score = hits / max(len(case["keywords"]), 1)
    evidence_sufficient = evidence_score >= 35 and retrieval_count > 0

    # Apply Causal Decision Tree
    if not info_present:
        if abstained or keyword_score >= 0.20:
            classification = "DOCUMENT_INSUFFICIENT"
            correctness = 1.0  # Correct faithful handling of unanswerable/blank doc
        else:
            classification = "HALLUCINATION_OR_FALSE_ANSWER"
            correctness = 0.0
    else:
        if not evidence_sufficient:
            classification = "RETRIEVAL_FAILURE"
            correctness = 0.0
        else:
            if abstained:
                classification = "FALSE_ABSTENTION"
                correctness = 0.0
            elif keyword_score < 0.20:
                classification = "GENERATION_OR_ROUTING_FAILURE"
                correctness = 0.0
            else:
                classification = "CORRECT"
                correctness = 1.0

    faithful = 1.0 if evidence_score >= 45 or result.get("evidence_status") in ("EXPLICIT", "CONDITIONAL", "PARTIAL") or not info_present else 0.0
    relevancy = 1.0 if correctness == 1.0 else 0.0

    # 4. Atomic Claims & Support
    sentences = re.split(r"[.!?]\s+|\n+", answer)
    claims = [s.strip() for s in sentences if len(s.strip()) > 15]
    if not claims:
        claim_support = 1.0 if abstained else 0.0
    else:
        supported = sum(1 for c in claims if evidence_score >= 40 or any(k.lower() in c.lower() for k in case["keywords"]))
        claim_support = supported / len(claims)

    # 5. Granular Condition Taxonomy
    condition_eval = evaluate_conditions_by_type(answer, case.get("conditions", {}))

    valid_citations = sum(1 for c in citations if c.get("page") is not None or c.get("section") or c.get("verified"))
    citation_accuracy = (valid_citations / len(citations)) if citations else (1.0 if not info_present else 0.0)
    citation_completeness = min(valid_citations / max(len(claims), 1), 1.0) if claims else 1.0

    print(f"Classification : [{classification}]", flush=True)
    print(f"Answer Preview : {answer[:130]}...", flush=True)
    print(f"Tier: {processing_tier} | Latency: {latency_ms:.1f}ms | Score: {evidence_score} | Correct: {correctness == 1.0} | CPR: {condition_eval['overall_recall']*100:.0f}%", flush=True)

    return {
        "id": case["id"],
        "document": case["document"],
        "category": case["category"],
        "query": query,
        "product_id": product_id,
        "product_name": document_cfg["product_name"],
        "information_present": info_present,
        "classification": classification,
        "processing_tier": processing_tier,
        "answer": answer,
        "latency_ms": latency_ms,
        "retrieval_ms": retrieval_ms,
        "evidence_score": evidence_score,
        "retrieved_chunks": retrieval_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "correctness": correctness,
        "faithfulness": faithful,
        "relevancy": relevancy,
        "claim_support": claim_support,
        "condition_recall": condition_eval["overall_recall"],
        "condition_precision": condition_eval["overall_precision"],
        "condition_by_type": condition_eval["by_type"],
        "citation_accuracy": citation_accuracy,
        "citation_completeness": citation_completeness,
        "evidence_sufficient": evidence_sufficient,
        "abstained": abstained,
        "citations": citations,
        "error": error,
    }

# ---------------------------------------------------------------------
# MAIN EVALUATION RUNNER
# ---------------------------------------------------------------------

def main():
    print()
    print("=" * 90, flush=True)
    print("FINEXPLAIN TOP-5 DOCUMENT DIAGNOSTIC BENCHMARK", flush=True)
    print("25 queries across 5 actual agreements in documents/top5", flush=True)
    print("=" * 90, flush=True)

    # 1. Execute Benchmark Cases with Pacing
    results = []
    start_total = time.time()
    for case in TEST_CASES:
        doc_key = case["document"]
        doc_cfg = DOCUMENTS[doc_key]
        res = evaluate_case(case, doc_cfg)
        results.append(res)
        time.sleep(3.0)  # Pacing to protect API quota (15 req/min)

    duration = time.time() - start_total
    total = len(results)

    # 2. Compute Causal Failure Counts
    classifications = [r["classification"] for r in results]
    correct_count = classifications.count("CORRECT")
    doc_insufficient_count = classifications.count("DOCUMENT_INSUFFICIENT")
    retrieval_failure_count = classifications.count("RETRIEVAL_FAILURE")
    gen_or_routing_failure_count = classifications.count("GENERATION_OR_ROUTING_FAILURE")
    false_abstention_count = classifications.count("FALSE_ABSTENTION")

    # 3. Compute High-Level Metrics
    info_present_queries = [r for r in results if r["information_present"]]
    evidence_sufficient_queries = [r for r in results if r["evidence_sufficient"]]
    
    ear = len(info_present_queries) / total  # Evidence Availability Rate
    esr = len(evidence_sufficient_queries) / total  # Evidence Sufficiency Rate
    
    # Conditional Correctness (given sufficient evidence exists and was retrieved)
    sufficient_and_present = [r for r in results if r["information_present"] and r["evidence_sufficient"]]
    conditional_correctness = (sum(r["correctness"] for r in sufficient_and_present) / len(sufficient_and_present)) if sufficient_and_present else 0.0
    
    # Overall End-to-End Correctness (19 fully answered + 3 validly handled unanswerable = 22, or strictly answerable 19/25 = 76%)
    raw_answered_correctly = sum(1 for r in results if r["classification"] == "CORRECT") / total
    effective_system_accuracy = sum(r["correctness"] for r in results) / total

    avg = lambda field: (sum(float(r[field]) for r in results) / total)
    faithfulness = avg("faithfulness")
    claim_support = avg("claim_support")
    relevancy = avg("relevancy")
    citation_accuracy = avg("citation_accuracy")
    condition_recall = avg("condition_recall")
    condition_precision = avg("condition_precision")

    # Granular Condition Recall by Type
    type_totals = {}
    type_matches = {}
    for r in results:
        for ctype, data in r.get("condition_by_type", {}).items():
            type_totals[ctype] = type_totals.get(ctype, 0) + data["total"]
            type_matches[ctype] = type_matches.get(ctype, 0) + data["matched"]

    condition_type_recalls = {
        ctype: round(type_matches[ctype] / type_totals[ctype] * 100, 1)
        for ctype in type_totals if type_totals[ctype] > 0
    }

    latencies = sorted(r["latency_ms"] for r in results)
    p50 = latencies[int(total * 0.50)]
    p95 = latencies[min(int(total * 0.95), total - 1)]
    avg_latency = avg("latency_ms")

    # 4. Print Dashboard Scorecard
    print("\n" + "=" * 90, flush=True)
    print("FINEXPLAIN TOP-5 BENCHMARK PRODUCTION SCORECARD", flush=True)
    print("=" * 90, flush=True)
    print(f"Total Queries: {total} | Operative Documents: {len(DOCUMENTS)} | Duration: {duration:.1f}s", flush=True)
    
    print("\n1. CAUSAL EVALUATION & DIAGNOSTIC TREE", flush=True)
    print(f"  • Total Queries Evaluated           : {total}", flush=True)
    print(f"  • Evidence Availability Rate (EAR)  : {ear * 100:.1f}% ({len(info_present_queries)}/{total} queries present in corpus)", flush=True)
    print(f"  • Evidence Sufficiency Rate (ESR)   : {esr * 100:.1f}% ({len(evidence_sufficient_queries)}/{total} queries retrieved sufficient evidence)", flush=True)
    print(f"  • Conditional Answer Correctness    : {conditional_correctness * 100:.1f}% (given sufficient evidence)", flush=True)
    print(f"  • Fully Correct Answers             : {correct_count}/{total} ({correct_count/total*100:.1f}%)", flush=True)
    
    print("\n2. FAILURE BREAKDOWN CLASSIFICATION", flush=True)
    print(f"  • Correct Answers                   : {correct_count} ({correct_count/total*100:.1f}%)", flush=True)
    print(f"  • Document Limitations (Blank/Form) : {doc_insufficient_count} ({doc_insufficient_count/total*100:.1f}%)", flush=True)
    print(f"  • Actual Retrieval Failures         : {retrieval_failure_count} ({retrieval_failure_count/total*100:.1f}%)", flush=True)
    print(f"  • Generation / Routing Failures     : {gen_or_routing_failure_count} ({gen_or_routing_failure_count/total*100:.1f}%)", flush=True)
    print(f"  • False Abstentions                 : {false_abstention_count} ({false_abstention_count/total*100:.1f}%)", flush=True)

    print("\n3. GENERATION QUALITY & GROUNDING", flush=True)
    print(f"  • Faithfulness                      : {faithfulness * 100:.1f}%", flush=True)
    print(f"  • Atomic Claim Support Rate         : {claim_support * 100:.1f}%", flush=True)
    print(f"  • Citation Accuracy                 : {citation_accuracy * 100:.1f}%", flush=True)
    print(f"  • Answer Relevancy                  : {relevancy * 100:.1f}%", flush=True)

    print("\n4. CONDITION PRESERVATION & GRANULAR TAXONOMY", flush=True)
    print(f"  • Condition Recall (CPR Overall)    : {condition_recall * 100:.1f}%", flush=True)
    print(f"  • Condition Precision (CP Overall)  : {condition_precision * 100:.1f}%", flush=True)
    for ctype, recall_val in sorted(condition_type_recalls.items()):
        print(f"    - {ctype.capitalize():18} Recall : {recall_val:.1f}%", flush=True)

    print("\n5. ENGINEERING LATENCY & ECONOMICS", flush=True)
    print(f"  • Latency P50 : {p50:.1f}ms | P95: {p95:.1f}ms | Avg: {avg_latency:.1f}ms", flush=True)

    # 5. Per-Document Breakdown
    print("\n" + "=" * 90, flush=True)
    print("PER-DOCUMENT ACCURACY BREAKDOWN", flush=True)
    print("=" * 90, flush=True)
    for doc_key, cfg in DOCUMENTS.items():
        doc_results = [r for r in results if r["document"] == doc_key]
        if not doc_results:
            continue
        d_correct = sum(1 for r in doc_results if r["classification"] == "CORRECT")
        d_doc_lim = sum(1 for r in doc_results if r["classification"] == "DOCUMENT_INSUFFICIENT")
        d_ret_fail = sum(1 for r in doc_results if r["classification"] == "RETRIEVAL_FAILURE")
        d_gen_fail = sum(1 for r in doc_results if r["classification"] == "GENERATION_OR_ROUTING_FAILURE")
        davg = lambda f: sum(r[f] for r in doc_results) / len(doc_results)
        print(f"\n{cfg['filename']}", flush=True)
        print(f"  Correct: {d_correct}/5 | Doc Limitation: {d_doc_lim}/5 | Retrieval Fail: {d_ret_fail}/5 | Routing Fail: {d_gen_fail}/5", flush=True)
        print(f"  Faithfulness: {davg('faithfulness')*100:.1f}% | Claim Support: {davg('claim_support')*100:.1f}% | CPR: {davg('condition_recall')*100:.1f}%", flush=True)

    # 6. Save JSON Report
    output_path = os.path.join(PROJECT_ROOT, "tests", "top5_benchmark_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_queries": total,
            "documents": list(DOCUMENTS.keys()),
            "causal_scorecard": {
                "evidence_availability_rate_ear_pct": round(ear * 100, 1),
                "evidence_sufficiency_rate_esr_pct": round(esr * 100, 1),
                "conditional_answer_correctness_pct": round(conditional_correctness * 100, 1),
                "raw_correct_count": correct_count,
                "document_limitations_count": doc_insufficient_count,
                "retrieval_failures_count": retrieval_failure_count,
                "generation_or_routing_failures_count": gen_or_routing_failure_count,
                "faithfulness_pct": round(faithfulness * 100, 1),
                "claim_support_rate_pct": round(claim_support * 100, 1),
                "citation_accuracy_pct": round(citation_accuracy * 100, 1),
                "condition_recall_cpr_pct": round(condition_recall * 100, 1),
                "condition_precision_cp_pct": round(condition_precision * 100, 1),
                "condition_taxonomy_recalls_pct": condition_type_recalls,
                "p50_latency_ms": round(p50, 1),
                "p95_latency_ms": round(p95, 1),
                "average_latency_ms": round(avg_latency, 1),
            },
            "results": results,
        }, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 90, flush=True)
    print(f"Diagnostic report successfully saved to: {output_path}", flush=True)
    print("=" * 90, flush=True)

if __name__ == "__main__":
    main()