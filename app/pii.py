from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    # Common 10-digit domestic and +84 international Vietnamese phone forms.
    "phone_vn": r"(?<!\d)(?:\+?84[ .-]?|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"(?<!\d)\d{12}(?!\d)",
    # Bank cards may have 13–19 digits, optionally separated by spaces or hyphens.
    "credit_card": r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
