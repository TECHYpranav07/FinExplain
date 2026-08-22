"""
PII and Secrets Redaction Guardrail.

Protects borrower privacy and prevents credential leakage by redacting:
1. PAN card numbers (India)
2. Aadhaar numbers (India)
3. Social Security Numbers (US)
4. Credit / Debit card numbers
5. Bank account numbers
6. API keys and Private credentials
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Sensitive Regex Patterns
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE)
AADHAAR_PATTERN = re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
BANK_ACCOUNT_PATTERN = re.compile(r"(?:a\/c|account\s*(?:no|number)?|acc\s*#)[\s:]*([0-9]{9,18})\b", re.IGNORECASE)
API_KEY_PATTERN = re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z-_]{35}|ghp_[a-zA-Z0-9]{36})\b")


class PIIGuard:
    """
    Automated PII & Secret Redaction Engine.
    """

    def redact_pii(self, text: str) -> Tuple[str, int]:
        """
        Redact sensitive identifiers from text.

        Returns
        -------
        (redacted_text, count_redacted)
        """
        if not text:
            return text, 0

        redacted = text
        count = 0

        # Redact API Keys & Secrets
        api_matches = API_KEY_PATTERN.findall(redacted)
        if api_matches:
            count += len(api_matches)
            redacted = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", redacted)

        # Redact PAN numbers
        pan_matches = PAN_PATTERN.findall(redacted)
        if pan_matches:
            count += len(pan_matches)
            redacted = PAN_PATTERN.sub("[REDACTED_PAN]", redacted)

        # Redact Aadhaar numbers
        aadhaar_matches = AADHAAR_PATTERN.findall(redacted)
        if aadhaar_matches:
            count += len(aadhaar_matches)
            redacted = AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", redacted)

        # Redact SSN numbers
        ssn_matches = SSN_PATTERN.findall(redacted)
        if ssn_matches:
            count += len(ssn_matches)
            redacted = SSN_PATTERN.sub("[REDACTED_SSN]", redacted)

        # Redact Credit Cards
        cc_matches = CREDIT_CARD_PATTERN.findall(redacted)
        if cc_matches:
            count += len(cc_matches)
            redacted = CREDIT_CARD_PATTERN.sub("[REDACTED_CARD_NUMBER]", redacted)

        # Redact Bank Accounts
        acc_matches = BANK_ACCOUNT_PATTERN.findall(redacted)
        if acc_matches:
            count += len(acc_matches)
            redacted = BANK_ACCOUNT_PATTERN.sub("Account: [REDACTED_ACCOUNT]", redacted)

        if count > 0:
            logger.info(f"[PIIGuard] Redacted {count} sensitive PII item(s)")

        return redacted, count


pii_guard = PIIGuard()
