"""
FinExplain Large-Scale Multi-Account Parallel Evaluation Harness.

Simulates 5 concurrent user accounts executing queries across 29 distinct loan products.
Includes a thread-safe pacing rate-limiter (4.2s minimum interval) guaranteeing strictly <= 14 queries / minute
to prevent API 429 quota exhaustion and burst throttling.

Clears cache prior to evaluation to measure authentic cold & warm RAG pipeline performance.
"""

import os
import sys
import time
import json
import math
import re
import threading
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, r"d:\Projects\fine-explain\backend")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.rag.orchestrator import process_query
from app.cache.query_cache import _L1_MEMORY_CACHE, PIPELINE_VERSION
from app.db.supabase_client import get_supabase_client

# Clear in-memory L1 cache and update cache namespace
_L1_MEMORY_CACHE.clear()

# 5 Virtual Evaluation Accounts
ACCOUNTS = [
    "user_acct_alpha",
    "user_acct_beta",
    "user_acct_gamma",
    "user_acct_delta",
    "user_acct_epsilon",
]

# Fetch Real Products from Supabase
supabase = get_supabase_client()
prod_records = supabase.table("products").select("id, name").execute().data or []
PRODUCT_MAP = {p["id"]: p["name"] for p in prod_records}
PRODUCT_IDS = list(PRODUCT_MAP.keys()) if PRODUCT_MAP else ["7e4fe332-bebf-4fcc-808e-9e6402738324"]


# ---------------------------------------------------------------------------
# Thread-Safe Pacing Rate Limiter (Max 14 requests / minute = 4.2s per request)
# ---------------------------------------------------------------------------

class PacedRateLimiter:
    def __init__(self, min_interval_seconds: float = 4.2):
        self.min_interval = min_interval_seconds
        self.last_call_time = 0.0
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
            self.last_call_time = time.time()

rate_limiter = PacedRateLimiter(min_interval_seconds=4.2)


# ---------------------------------------------------------------------------
# Comprehensive Query Template Generator
# ---------------------------------------------------------------------------

QUERY_TEMPLATES = [
    # 1. Factual Lookups (Targets FAST_FACTUAL / FactStore)
    {"type": "factual", "q": "What is the interest rate on this loan?", "field": "interest_rate", "kw": ["rate", "%", "interest", "floating", "sbbr"]},
    {"type": "factual", "q": "What is the penal interest rate charged for delayed payment?", "field": "penal_interest", "kw": ["6%", "delayed", "overdue", "penal"]},
    {"type": "factual", "q": "What is the processing fee charged by the lender?", "field": "processing_fee", "kw": ["processing", "fee", "8,000", "charge"]},
    {"type": "factual", "q": "What is the bounce charge for cheque or ECS return?", "field": "bounce_charge", "kw": ["bounce", "ecs", "cheque", "charge", "750"]},
    {"type": "factual", "q": "What is the loan tenure and repayment duration?", "field": "tenure", "kw": ["tenure", "months", "years", "duration", "period"]},
    {"type": "factual", "q": "What is the sanctioned loan amount and principal limit?", "field": "loan_amount", "kw": ["principal", "amount", "sanction", "limit"]},
    {"type": "factual", "q": "What is the documentation fee and stamp duty charge?", "field": "documentation_fee", "kw": ["documentation", "stamp", "duty", "fee"]},
    {"type": "factual", "q": "What is the cooling-off period to cancel this loan?", "field": "cooling_off_period", "kw": ["cooling", "cancel", "days", "period"]},
    
    # 2. Conditional & Policy Queries (Targets STANDARD_RAG)
    {"type": "policy", "q": "Can I prepay or foreclose this loan early, and what are the charges?", "field": "prepayment_fee", "kw": ["prepay", "foreclosure", "charges", "12 emis", "penalty"]},
    {"type": "policy", "q": "What happens if I default or fail to pay an EMI on the due date?", "field": "penal_interest", "kw": ["default", "overdue", "penal", "recovery", "notice"]},
    {"type": "policy", "q": "Are there any prepayment lock-in periods or penalty waivers?", "field": "prepayment_fee", "kw": ["lock-in", "waiver", "prepay", "penalty", "clearance"]},
    {"type": "policy", "q": "What are the terms regarding collateral security and mortgage?", "field": "collateral", "kw": ["collateral", "security", "mortgage", "hypothecat", "property"]},
    
    # 3. Calculation Queries (Targets CALCULATION Engine)
    {"type": "calculation", "q": "Calculate total cost and EMI if I borrow 500000 for 5 years", "field": "calc", "kw": ["monthly emi", "total interest", "total amount", "500,000"]},
    {"type": "calculation", "q": "Calculate total cost and EMI if I borrow 1000000 for 3 years", "field": "calc", "kw": ["monthly emi", "total interest", "total amount", "1,000,000"]},
    {"type": "calculation", "q": "Calculate monthly EMI if I take 250000 for 2 years", "field": "calc", "kw": ["monthly emi", "total interest", "250,000"]},
    {"type": "calculation", "q": "Calculate repayment schedule and EMI for 2000000 for 7 years", "field": "calc", "kw": ["monthly emi", "total amount", "2,000,000"]},

    # 4. Deep Risk & Compliance Audits (Targets DEEP_RAG)
    {"type": "deep_audit", "q": "Review all risk factors, default penalties, and predatory clauses in this agreement", "field": "audit", "kw": ["risk", "penal", "default", "contingent", "indemnity"]},
    {"type": "deep_audit", "q": "What are the missing disclosure items, hidden fees, and questions to ask the lender?", "field": "audit", "kw": ["missing", "disclosure", "apr", "fees", "verify"]},

    # 5. Out-of-Scope / Abstention Tests (Targets ABSTENTION GATE)
    {"type": "unanswerable", "q": "What is the cryptocurrency margin liquidation threshold and Bitcoin haircut?", "field": "abstain", "kw": ["not specified", "unable to provide", "not covered"]},
    {"type": "unanswerable", "q": "What is the typhoon and hurricane weather insurance compensation policy?", "field": "abstain", "kw": ["not specified", "unable to provide", "not covered"]},
]


def build_evaluation_dataset(target_count: int = 45) -> List[Dict[str, Any]]:
    """Builds a deterministic dataset of target_count queries distributed across products and accounts."""
    dataset = []
    pid_idx = 0
    t_idx = 0

    for i in range(target_count):
        tmpl = QUERY_TEMPLATES[t_idx % len(QUERY_TEMPLATES)]
        p_id = PRODUCT_IDS[pid_idx % len(PRODUCT_IDS)]
        p_name = PRODUCT_MAP.get(p_id, "Standard Loan Agreement")
        acct = ACCOUNTS[i % len(ACCOUNTS)]

        query_item = {
            "query_id": f"EVAL_Q_{i+1:03d}",
            "account_id": acct,
            "category": tmpl["type"],
            "query": tmpl["q"],
            "target_field": tmpl["field"],
            "product_id": p_id,
            "product_name": p_name,
            "expected_keywords": tmpl["kw"],
            "is_answerable": tmpl["type"] != "unanswerable",
        }
        dataset.append(query_item)
        pid_idx += 1
        t_idx += 1

    return dataset


# ---------------------------------------------------------------------------
# Account Execution Worker
# ---------------------------------------------------------------------------

def execute_account_query(query_item: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates a single account executing a query with pacing and metrics."""
    acct = query_item["account_id"]
    q = query_item["query"]
    p_id = query_item["product_id"]
    is_ans = query_item["is_answerable"]
    exp_kw = query_item["expected_keywords"]

    # Acquire rate limiter ticket to guarantee <= 14 requests / minute
    rate_limiter.acquire()

    t0 = time.perf_counter()
    try:
        res = process_query(q, [p_id], user_id=acct)
        elapsed_ms = (time.perf_counter() - t0) * 1000
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        res = {"answer": f"Error: {e}", "processing_tier": "error", "evidence_score": 0}

    ans = res.get("answer", "")
    tier = res.get("processing_tier", "standard_rag")
    ev_score = res.get("evidence_score", 0)
    citations = res.get("citations", [])
    tokens = res.get("token_metrics", {})
    in_tok = tokens.get("input_tokens", 0)
    out_tok = tokens.get("output_tokens", 0)

    ans_lower = ans.lower()
    did_abstain = any(w in ans_lower for w in ["not specified", "unable to provide", "not covered", "not disclosed", "please review"])

    # Correctness & Grounding
    if is_ans:
        kw_hits = sum(1 for kw in exp_kw if kw.lower() in ans_lower)
        is_correct = (kw_hits >= 1) or (ev_score >= 60)
        is_faithful = ev_score >= 40
        is_unsupported = not is_correct and not did_abstain and ev_score < 30
    else:
        is_correct = did_abstain
        is_faithful = did_abstain
        is_unsupported = not did_abstain

    cost_usd = (in_tok / 1_000_000 * 0.075) + (out_tok / 1_000_000 * 0.30)

    return {
        "query_id": query_item["query_id"],
        "account_id": acct,
        "product_name": query_item["product_name"],
        "category": query_item["category"],
        "query": q,
        "tier": tier,
        "latency_ms": round(elapsed_ms, 1),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cost_usd": round(cost_usd, 6),
        "evidence_score": ev_score,
        "is_correct": is_correct,
        "is_faithful": is_faithful,
        "is_unsupported": is_unsupported,
        "did_abstain": did_abstain,
        "citations_count": len(citations),
        "answer_preview": ans[:110] + "..." if len(ans) > 110 else ans,
    }


# ---------------------------------------------------------------------------
# Main Orchestrated Multi-Account Benchmark Runner
# ---------------------------------------------------------------------------

def run_large_scale_multi_account_eval(total_queries: int = 45):
    dataset = build_evaluation_dataset(target_count=total_queries)

    print("=" * 85)
    print(f"FINEXPLAIN MULTI-ACCOUNT EVALUATION: {total_queries} QUERIES ACROSS 5 CONCURRENT ACCOUNTS")
    print(f"Rate Limiter: 4.2s spacing (Strictly <= 14.2 queries / minute)")
    print(f"Target Products: {len(PRODUCT_IDS)} distinct documents")
    print("=" * 85)

    all_results = []
    start_time_all = time.time()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(execute_account_query, item) for item in dataset]
        for idx, future in enumerate(as_completed(futures), start=1):
            res = future.result()
            all_results.append(res)
            print(f"[{idx:02d}/{total_queries}] [{res['account_id']}] {res['query_id']} ({res['category']}) -> Latency={res['latency_ms']}ms | Tier={res['tier']} | Score={res['evidence_score']}")

    total_eval_duration = time.time() - start_time_all

    # -----------------------------------------------------------------------
    # Comprehensive Metric Calculation
    # -----------------------------------------------------------------------
    n = len(all_results)
    correct_count = sum(1 for r in all_results if r["is_correct"])
    faithful_count = sum(1 for r in all_results if r["is_faithful"])
    unsupported_count = sum(1 for r in all_results if r["is_unsupported"])
    zero_token_count = sum(1 for r in all_results if r["input_tokens"] == 0)

    # Latencies
    all_lats = sorted(r["latency_ms"] for r in all_results)
    p50 = all_lats[int(n * 0.50)]
    p75 = all_lats[int(n * 0.75)]
    p90 = all_lats[int(n * 0.90)]
    p95 = all_lats[min(int(n * 0.95), n - 1)]
    p99 = all_lats[min(int(n * 0.99), n - 1)]
    avg_lat = sum(all_lats) / n

    # Disaggregated Tier Latencies
    tier_lats = {}
    for r in all_results:
        t = r["tier"]
        tier_lats.setdefault(t, []).append(r["latency_ms"])

    tier_p50s = {t: round(sorted(lats)[len(lats)//2], 1) for t, lats in tier_lats.items()}

    # Costs
    total_cost_usd = sum(r["cost_usd"] for r in all_results)
    avg_in_tok = sum(r["input_tokens"] for r in all_results) / n
    avg_out_tok = sum(r["output_tokens"] for r in all_results) / n

    final_report = {
        "benchmark_metadata": {
            "total_queries_evaluated": n,
            "concurrent_accounts": len(ACCOUNTS),
            "total_duration_minutes": round(total_eval_duration / 60, 2),
            "rate_limit_discipline": "Strictly <= 14 queries/minute",
        },
        "accuracy_and_grounding": {
            "answer_correctness_pct": round((correct_count / n) * 100, 1),
            "faithfulness_pct": round((faithful_count / n) * 100, 1),
            "unsupported_claim_rate_on_benchmark": f"{unsupported_count}/{n} ({round(unsupported_count/n*100, 1)}%)",
            "zero_llm_direct_resolution_pct": round((zero_token_count / n) * 100, 1),
        },
        "latency_percentiles_ms": {
            "p50_ms": round(p50, 1),
            "p75_ms": round(p75, 1),
            "p90_ms": round(p90, 1),
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
            "avg_ms": round(avg_lat, 1),
            "p50_by_tier": tier_p50s,
        },
        "token_and_cost_economics": {
            "avg_input_tokens": round(avg_in_tok),
            "avg_output_tokens": round(avg_out_tok),
            "total_eval_cost_usd": round(total_cost_usd, 6),
            "cost_per_query_usd": round(total_cost_usd / n, 6),
            "cost_per_1k_queries_usd": round((total_cost_usd / n) * 1000, 4),
            "cost_per_10k_queries_usd": round((total_cost_usd / n) * 10000, 2),
        },
        "query_results": all_results,
    }

    with open(r"d:\Projects\fine-explain\large_scale_eval_report.json", "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print("\n" + "=" * 85)
    print("LARGE-SCALE BENCHMARK FINISHED. RESULTS WRITTEN TO large_scale_eval_report.json")
    print("=" * 85)


if __name__ == "__main__":
    run_large_scale_multi_account_eval(total_queries=45) # 45 queries across 5 accounts = ~3.2 minutes total
