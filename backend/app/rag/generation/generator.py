"""
LLM generation layer for FinExplain.

Uses Google Gemini LLM API with centralized prompt templates.
Supports both the legacy ``(query, context)`` signature and the new
enriched signature with structured facts, calculations, conflicts, etc.
"""

import json
import logging
from app.external.llm_client import llm, client
from app.core.constants import DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)
from app.rag.generation.prompt_templates import (
    SYSTEM_PROMPT_FINANCIAL_EXPERT,
    QA_USER_PROMPT_TEMPLATE,
    LOAN_REVIEW_PROMPT,
    BEFORE_CONFIRMATION_PROMPT,
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
) -> Dict[str, Any]:
    """
    Generate an answer using Gemini LLM with evidence-first prompting.

    Backward-compatible: callers passing only ``(query, context)`` still work.
    When the enriched kwargs are provided, uses the full structured QA prompt.
    """
    # Build the user prompt
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
    )

    try:
        answer_text = llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_FINANCIAL_EXPERT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )

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
                {"role": "system", "content": SYSTEM_PROMPT_FINANCIAL_EXPERT},
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
                {"role": "system", "content": SYSTEM_PROMPT_FINANCIAL_EXPERT},
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