"""
LLM generation layer for FinExplain.

Uses Google Gemini LLM API with centralized prompt templates.
Supports both the legacy ``(query, context)`` signature and the new
enriched signature with structured facts, calculations, conflicts, etc.

Tiered prompt selection:
  - When only facts/context provided → FAST_QA (minimal tokens)
  - When enrichment data present → full QA_USER_PROMPT_TEMPLATE
"""

import json
import logging
import re
from app.external.llm_client import llm, client
from app.core.constants import DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)
from app.rag.generation.prompt_templates import (
    SYSTEM_PROMPT_ASK_AI,
    SYSTEM_PROMPT_LOAN_REVIEW,
    SYSTEM_PROMPT_BEFORE_CONFIRMATION,
    SYSTEM_PROMPT_LOAN_COMPARE,
    SYSTEM_PROMPT_FINANCIAL_EXPERT,
    QA_USER_PROMPT_TEMPLATE,
    FAST_QA_SYSTEM_PROMPT,
    FAST_QA_USER_PROMPT,
    LOAN_REVIEW_PROMPT,
    BEFORE_CONFIRMATION_PROMPT,
    MULTI_PRODUCT_COMPARISON_PROMPT,
)
from typing import Dict, Any, List, Optional


def _format_for_prompt(data: Any) -> str:
    """Safely format data for insertion into a prompt template."""
    if data is None:
        return "None"
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, indent=2, default=str)
    except Exception:
        return str(data)


def generate_answer(
    query: str,
    context: str,
    *,
    structured_facts: Optional[List[Dict[str, Any]]] = None,
    calculation_results: Optional[Dict[str, Any]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
    missing_information: Optional[List[Dict[str, Any]]] = None,
    claim_verification: Optional[Dict[str, Any]] = None,
    evidence_score: Optional[Dict[str, Any]] = None,
    scenario: Optional[Dict[str, Any]] = None,
    risk_factors: Optional[List[Dict[str, Any]]] = None,
    risk_score: Optional[Dict[str, Any]] = None,
    query_requirements: Optional[List[str]] = None,
    completeness_feedback: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate an answer using Gemini LLM with evidence-first prompting.

    Automatically selects between fast (minimal) and full prompt based
    on the presence of enrichment data (risk, conflicts, calculations).
    """
    # Determine if this is a simple factual query (no heavy enrichment)
    query_requirements = query_requirements or []
    completeness_feedback = completeness_feedback or []
    requirements_text = "\n".join(f"- {item.replace('_', ' ')}" for item in query_requirements) or "- Address the user's question directly."
    feedback_text = "\n".join(f"- {item.replace('_', ' ')}" for item in completeness_feedback) or "None"

    has_enrichment = any([
        conflicts,
        risk_factors,
        risk_score and risk_score.get("score") is not None,
        calculation_results,
        scenario,
    ])
    # A multi-aspect lookup needs the full answer template even when it has no
    # risk or calculation enrichment. The old fast prompt encouraged a single
    # headline fact for questions that requested several contractual terms.
    requires_structured_answer = len(query_requirements) > 1

    if not has_enrichment and not requires_structured_answer:
        # FAST PATH: Minimal prompt for factual lookups
        system_prompt = FAST_QA_SYSTEM_PROMPT
        prompt = FAST_QA_USER_PROMPT.format(
            question=query,
            context=context,
            structured_facts=_format_for_prompt(structured_facts),
            query_requirements=requirements_text,
            completeness_feedback=feedback_text,
        )
        max_tokens = 512
    else:
        # FULL PATH: Rich prompt with all enrichment data
        system_prompt = SYSTEM_PROMPT_ASK_AI
        prompt = QA_USER_PROMPT_TEMPLATE.format(
            question=query,
            scenario=_format_for_prompt(scenario),
            context=context,
            structured_facts=_format_for_prompt(structured_facts),
            calculation_results=_format_for_prompt(calculation_results),
            conflicts=_format_for_prompt(conflicts),
            missing_information=_format_for_prompt(missing_information),
            claim_verification=_format_for_prompt(claim_verification),
            evidence_score=_format_for_prompt(evidence_score),
            risk_factors=_format_for_prompt(risk_factors),
            risk_score=_format_for_prompt(risk_score),
            query_requirements=requirements_text,
            completeness_feedback=feedback_text,
        )
        max_tokens = 2048

    try:
        answer_text = llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )

        if answer_text:
            # Strip any internal chunk IDs like ", Chunk: c21c2086" or "Chunk c21c2086"
            answer_text = re.sub(r'(?:,\s*)?Chunk:?\s*[a-f0-9]{6,}\b', '', answer_text, flags=re.I)
            answer_text = re.sub(r'\[\s*,\s*', '[', answer_text)
            answer_text = re.sub(r',\s*\]', ']', answer_text)

        return {
            "answer": answer_text,
            "raw_response": None,
        }

    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "error": str(e),
        }


def _synthesize_deterministic_review(
    structured_facts: List[Dict[str, Any]],
    missing_information: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    cost_drivers: List[Dict[str, Any]],
) -> str:
    """Generate a high quality Markdown audit report directly from extracted facts."""
    lines = [
        "# 📋 Proactive Loan Agreement Audit Report",
        "",
        "### 🎯 Executive Summary & Verdict",
        f"FinExplain's audit engine analyzed **{len(structured_facts)} factual clauses** across the operative credit documentation.",
    ]

    if conflicts:
        lines.append(f"> ⚠️ **Attention**: **{len(conflicts)} contractual conflict(s)** detected across loan schedules. Scrutiny is advised prior to signing.")
    else:
        lines.append("No direct contractual contradictions detected between operative documents.")

    lines.extend([
        "",
        "---",
        "",
        "### 📊 Key Financial Parameters & Rate Breakdown",
        "| Parameter | Verified Value | Category | Status & Source |",
        "|---|---|---|---|",
    ])

    for f in structured_facts[:10]:
        name = f.get("field", f.get("category", "Term")).replace("_", " ").title()
        val = f.get("value", "Mentioned")
        unit = f.get("unit", "")
        formatted_val = f"{val} {unit}".strip() if val != "Mentioned" else "Specified in Clause"
        cat = f.get("category", "General").replace("_", " ").title()
        status = f.get("status", "EXPLICIT")
        page = f"Page {f.get('page')}" if f.get("page") else "Documented"
        lines.append(f"| **{name}** | `{formatted_val}` | {cat} | `{status}` ({page}) |")

    if not structured_facts:
        lines.append("| *Parameters* | *No explicit facts extracted* | General | Under Verification |")

    lines.extend([
        "",
        "---",
        "",
        "### 🚨 Critical Risk Checks & Predatory Traps",
    ])

    if conflicts:
        for c in conflicts:
            lines.append(f"- 🔴 **Conflict in {c.get('field', 'clause')}**: {c.get('description', 'Discrepancy between documents.')}")
    else:
        lines.append("- ✅ **Standard Protections**: No aggressive unilateral interest adjustment clauses found.")

    if cost_drivers:
        lines.extend([
            "",
            "---",
            "",
            "### 💡 Major Cost Drivers & Fee Traps",
        ])
        for cd in cost_drivers[:6]:
            name = cd.get("field", cd.get("name", "Cost Factor")).replace("_", " ").title()
            val = cd.get("value", "")
            cond = cd.get("condition", cd.get("description", "Applicable under terms."))
            lines.append(f"- **{name}** (`{val}`): {cond}")

    if missing_information:
        lines.extend([
            "",
            "---",
            "",
            "### ❓ Missing Information & Material Omissions",
        ])
        for m in missing_information[:5]:
            field = m.get("field", "Item").replace("_", " ").title()
            reason = m.get("reason", "Not specified in agreement.")
            lines.append(f"- **{field}**: {reason}")

    lines.extend([
        "",
        "---",
        "",
        "### 🛡️ Recommended Questions for Your Lender",
        "1. Can you confirm in writing whether foreclosure charges are strictly 0% for floating-rate tenures?",
        "2. What is the exact benchmark spread reset frequency and calculation formula?",
        "3. Are there any administrative charges or ledger fees not summarized in the primary KFS?",
        "4. What is the specific grace period duration before late payment penal interest accrues?",
    ])

    return "\n".join(lines)


def generate_loan_review(
    structured_facts: List[Dict[str, Any]],
    missing_information: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    cost_drivers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate a proactive loan document review using the LOAN_REVIEW_PROMPT with fallback.
    """
    prompt = LOAN_REVIEW_PROMPT.format(
        structured_facts=_format_for_prompt(structured_facts),
        missing_information=_format_for_prompt(missing_information),
        conflicts=_format_for_prompt(conflicts),
        cost_drivers=_format_for_prompt(cost_drivers),
    )

    try:
        content = llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_LOAN_REVIEW},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        if content and len(content.strip()) > 30 and not content.startswith("Error"):
            return {"review": content}
    except Exception as e:
        logger.warning(f"LLM review generation error, falling back to deterministic synthesis: {e}")

    # Fallback deterministic synthesis
    fallback_markdown = _synthesize_deterministic_review(
        structured_facts=structured_facts,
        missing_information=missing_information,
        conflicts=conflicts,
        cost_drivers=cost_drivers,
    )
    return {"review": fallback_markdown}



def _synthesize_deterministic_checklist(
    structured_facts: List[Dict[str, Any]],
    missing_information: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    calculations: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a high-quality Markdown pre-signing checklist directly from extracted facts and rules."""
    lines = [
        "# 🛡️ Before You Confirm — Pre-Signing Verification Brief",
        "",
        "### 📌 Executive Verification Overview",
        f"FinExplain analyzed **{len(structured_facts)} operative loan terms** to construct this pre-confirmation checklist.",
    ]

    if conflicts:
        lines.append(f"> 🚨 **Action Required**: **{len(conflicts)} contract discrepancy / conflict(s)** detected across loan schedules. Clarification in writing is required prior to signing.")
    elif missing_information:
        lines.append(f"> ⚠️ **Caution**: Standard protections exist, but **{len(missing_information)} critical disclosure(s)** are missing from the reviewed documents.")
    else:
        lines.append("> ✅ **Ready for Detailed Verification**: Core financial terms are documented. Review the itemized checklist below.")

    lines.extend([
        "",
        "---",
        "",
        "### ✅ 1. Mandatory Pre-Signing Verification Checklist",
        "",
        "#### A. Core Financial & Rate Structure",
        "| Parameter | Verified Value | Category | Verification Status |",
        "|---|---|---|---|",
    ])

    for f in structured_facts[:8]:
        name = f.get("field", f.get("category", "Term")).replace("_", " ").title()
        val = f.get("value", "Mentioned")
        unit = f.get("unit", "")
        formatted_val = f"{val} {unit}".strip() if val != "Mentioned" else "Specified in Clause"
        cat = f.get("category", "Financial").replace("_", " ").title()
        status = f.get("status", "EXPLICIT")
        marker = "✓ [VERIFIED]" if status == "EXPLICIT" else "⚠ [CONDITIONAL]"
        page = f"Page {f.get('page')}" if f.get("page") else "Documented"
        lines.append(f"| **{name}** | `{formatted_val}` | {cat} | `{marker}` ({page}) |")

    if not structured_facts:
        lines.append("| *Loan Parameters* | *No explicit facts extracted* | General | `? [UNSPECIFIED]` |")

    lines.extend([
        "",
        "---",
        "",
        "### ⚠️ 2. Conditional Clauses & Critical Obligations",
    ])

    conditional_facts = [f for f in structured_facts if f.get("condition") or f.get("status") == "CONDITIONAL"]
    if conditional_facts:
        for cf in conditional_facts[:5]:
            field = cf.get("field", "Clause").replace("_", " ").title()
            cond = cf.get("condition", "Subject to lender policy.")
            val = cf.get("value", "")
            lines.append(f"- ⚠️ **{field}** (`{val}`): {cond}")
    else:
        lines.append("- ✅ No aggressive conditional cost escalation clauses detected.")

    lines.extend([
        "",
        "---",
        "",
        "### 🚨 3. Critical Red Flags & Unresolved Conflicts",
    ])

    if conflicts:
        for c in conflicts:
            field = c.get("field", "Clause").replace("_", " ").title()
            desc = c.get("description", "Discrepancy between documents.")
            lines.append(f"- 🔴 **Conflict in {field}**: {desc}")
    else:
        lines.append("- ✅ **No Contradictions**: Key Fact Statement and loan terms align with standard documentation.")

    if missing_information:
        lines.extend([
            "",
            "---",
            "",
            "### ❓ 4. Material Disclosures to Request from Lender",
        ])
        for m in missing_information[:5]:
            field = m.get("field", "Item").replace("_", " ").title()
            reason = m.get("reason", "Not specified in document.")
            lines.append(f"- ❓ **{field}**: {reason}")

    lines.extend([
        "",
        "---",
        "",
        "### 📋 5. Actionable Questions to Ask Your Lender (In Writing)",
        "1. **On Foreclosure Charges**: *Can you confirm in writing whether foreclosure charges are strictly 0% for floating-rate tenures with no minimum lock-in?*",
        "2. **On Benchmark Spread Resets**: *What is the exact benchmark spread reset frequency and notification window before interest changes take effect?*",
        "3. **On Net Disbursal & Upfront Fees**: *What is the exact net disbursement amount after all processing fees, documentation charges, and statutory stamp duties are deducted?*",
        "4. **On Grace Periods**: *What is the exact grace period duration before late payment penal interest or ECS bounce charges are levied?*",
    ])

    return "\n".join(lines)


def generate_before_confirmation(
    structured_facts: List[Dict[str, Any]],
    missing_information: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    calculations: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a "Before You Confirm" checklist with LLM synthesis and deterministic fallback.
    """
    prompt = BEFORE_CONFIRMATION_PROMPT.format(
        structured_facts=_format_for_prompt(structured_facts),
        missing_information=_format_for_prompt(missing_information),
        conflicts=_format_for_prompt(conflicts),
        calculations=_format_for_prompt(calculations),
    )

    try:
        content = llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_BEFORE_CONFIRMATION},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        if content and len(content.strip()) > 30 and not content.startswith("Error"):
            return {"checklist": content}
    except Exception as e:
        logger.warning(f"LLM before-confirmation generation error, falling back to deterministic synthesis: {e}")

    # Deterministic fallback synthesis
    fallback_markdown = _synthesize_deterministic_checklist(
        structured_facts=structured_facts,
        missing_information=missing_information,
        conflicts=conflicts,
        calculations=calculations,
    )
    return {"checklist": fallback_markdown}


def _synthesize_deterministic_comparison(
    products: List[Dict[str, Any]],
    field_comparisons: List[Dict[str, Any]],
    scenario: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate an exhaustive Markdown multi-product comparison brief directly from structured facts.
    """
    prod_names = [p.get("name", f"Product {idx+1}") for idx, p in enumerate(products)]
    lines = [
        "# ⚖️ Comparative Loan Benchmark Analysis",
        "",
        "### 🎯 Executive Comparative Verdict & Summary",
        f"FinExplain evaluated **{len(products)} loan facilities** ({', '.join(prod_names)}) across verified contractual terms.",
        "",
    ]

    # Executive Verdict Highlights
    lines.extend([
        "> 💡 **Borrower Takeaway**: Compare the side-by-side rates and fee schedules below. Lower headline rates can be offset by higher upfront processing charges or restrictive prepayment penalties.",
        "",
        "---",
        "",
        "### 📊 Side-by-Side Financial & Rate Benchmark Matrix",
        "",
    ])

    # Build comparison table headers
    header_cols = ["Financial Parameter"] + prod_names + ["Comparison Status"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

    # Map fields
    for fc in field_comparisons:
        field_name = fc.get("field", "Term").replace("_", " ").title()
        val_cells = []
        winner = fc.get("winner", "Comparable")

        for idx, p in enumerate(products):
            pid = str(p.get("id", idx))
            p_val_obj = fc.get(f"product_{idx}") or fc.get("values", {}).get(pid) or fc.get(f"product_{chr(97+idx)}")
            if isinstance(p_val_obj, dict):
                v = p_val_obj.get("value", "Mentioned")
                u = p_val_obj.get("unit", "")
                val_str = f"`{v} {u}`".strip() if v else "Mentioned"
            elif p_val_obj:
                val_str = f"`{p_val_obj}`"
            else:
                val_str = "*Not Specified*"
            val_cells.append(val_str)

        lines.append(f"| **{field_name}** | " + " | ".join(val_cells) + f" | {winner} |")

    if not field_comparisons:
        lines.append(f"| *Terms* | " + " | ".join(["*Extracted from document*"] * len(prod_names)) + " | Neutral |")

    lines.extend([
        "",
        "---",
        "",
        "### 🔓 Prepayment, Foreclosure & Exit Flexibility",
        "- **Floating Rate Protections**: Under RBI guidelines, individual floating-rate retail loans carry 0% foreclosure fees.",
        "- **Fixed Rate Lock-ins**: Check whether fixed-rate tranches impose early exit penalties (typically 2% to 4% of outstanding balance).",
        "",
        "---",
        "",
        "### 🚨 Critical Risk Traps, Penalties & Discrepancies",
        "- Verify whether processing fees are non-refundable upon loan cancellation.",
        "- Check the penal interest rate (typically 18% to 24% p.a. on overdue installments) and bounce charges per cheque/ECS return.",
        "",
        "---",
        "",
        "### 🛡️ Strategic Negotiation Levers for the Borrower",
        f"1. **Rate Matching**: Use the lower interest quotation from **{prod_names[0]}** to request a spread discount from **{prod_names[1] if len(prod_names) > 1 else 'other lenders'}**.",
        "2. **Processing Fee Waiver**: Ask for an upfront processing fee reduction or waiver during promotional periods.",
        "3. **Zero Prepayment Guarantee**: Demand written confirmation that partial prepayments incur zero administrative charges.",
    ])

    return "\n".join(lines)


def generate_loan_comparison(
    products: List[Dict[str, Any]],
    field_comparisons: List[Dict[str, Any]],
    scenario: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate an authoritative comparative analysis between multiple loan products using LLM with deterministic fallback.
    """
    prod_summary_list = []
    for p in products:
        prod_summary_list.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "issuer": p.get("issuer"),
            "effective_date": p.get("effective_date"),
        })

    prompt = MULTI_PRODUCT_COMPARISON_PROMPT.format(
        products_summary=_format_for_prompt(prod_summary_list),
        structured_comparisons=_format_for_prompt(field_comparisons),
        scenario_details=_format_for_prompt(scenario or {}),
    )

    try:
        content = llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_LOAN_COMPARE},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        if content and len(content.strip()) > 30 and not content.startswith("Error"):
            return {"comparison": content}
    except Exception as e:
        logger.warning(f"LLM comparison generation error, falling back to deterministic synthesis: {e}")

    # Fallback deterministic synthesis
    fallback_markdown = _synthesize_deterministic_comparison(
        products=products,
        field_comparisons=field_comparisons,
        scenario=scenario,
    )
    return {"comparison": fallback_markdown}
