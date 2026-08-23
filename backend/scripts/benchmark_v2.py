import sys, time, uuid, json
sys.path.insert(0, r'd:\Projects\fine-explain\backend')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.rag.orchestrator import process_query

with open(r'd:\Projects\fine-explain\rag_multi_doc_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
p_id = data['products'][0]['id']

test_queries = [
    ('1. FAST_FACTUAL (Penal Interest)', 'What is the penal interest rate?'),
    ('2. FAST_FACTUAL (Interest Rate)', 'What is the interest rate?'),
    ('3. FAST_FACTUAL (Processing Fee)', 'What is the processing fee?'),
    ('4. CALCULATION (EMI Math)', 'Calculate total cost and EMI if I borrow 500000 for 5 years'),
    ('5. STANDARD_RAG (Policy & Terms)', 'Can I prepay or close early?'),
    ('6. DEEP_RAG (Full Risk Audit)', 'Review all risk factors and penalty terms')
]

print('=============================================================================')
print('FINEXPLAIN V2 BENCHMARK RUNNER (DETERMINISTIC FACT LAYER & MULTI-TIER RAG)')
print('=============================================================================\n')

for label, q in test_queries:
    t0 = time.perf_counter()
    res = process_query(q, [p_id])
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    tokens = res.get('token_metrics', {})
    print(f'[{label}]')
    print(f'  Query:        "{q}"')
    print(f'  Latency:      {elapsed_ms:>7.1f} ms  ({elapsed_ms/1000:>5.3f}s)')
    print(f'  Tier:         {res.get("processing_tier")}')
    print(f'  LLM Tokens:   Input={tokens.get("input_tokens", 0)}, Output={tokens.get("output_tokens", 0)}, Total={tokens.get("total_tokens", 0)} (Model: {tokens.get("model")})')
    print(f'  Evidence:     Score={res.get("evidence_score", 0)}/100 ({res.get("confidence_label")}) | Status={res.get("evidence_status")}')
    print(f'  Answer:       {res.get("answer", "")[:250]}')
    print('-----------------------------------------------------------------------------\n')
