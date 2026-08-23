from app.rag.enhancement.query_router import (
    QueryTier,
    classify_query_tier,
    extract_query_requirements,
    is_compound_query,
    missing_answer_requirements,
)


def test_single_interest_lookup_keeps_fast_path():
    tier, field = classify_query_tier("What is the interest rate?", intent="lookup")

    assert tier == QueryTier.FAST_FACTUAL
    assert field == "interest_rate"


def test_multi_attribute_interest_query_uses_standard_rag():
    query = "What interest rate, EPI calculation, and repayment terms apply?"

    assert is_compound_query(query)
    assert classify_query_tier(query, intent="lookup") == (QueryTier.STANDARD_RAG, None)
    assert extract_query_requirements(query) == [
        "interest_rate",
        "epi_calculation",
        "repayment_terms",
    ]


def test_preclosure_conditions_do_not_use_single_fact_fast_path():
    query = "What are the prepayment, lock-in period, and foreclosure conditions?"

    assert is_compound_query(query)
    assert classify_query_tier(query, intent="lookup") == (QueryTier.STANDARD_RAG, None)


def test_missing_answer_requirements_are_reported():
    requirements = ["interest_rate", "epi_calculation", "repayment_terms"]
    answer = "The interest rate is 10.50% [Page 1]."

    assert missing_answer_requirements(answer, requirements) == [
        "epi_calculation",
        "repayment_terms",
    ]
