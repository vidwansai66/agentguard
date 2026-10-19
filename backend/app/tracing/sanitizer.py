import re
from typing import Any

SENSITIVE_KEY_PATTERNS = [
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
]

SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9\-_.]+", re.IGNORECASE),
    re.compile(r"(?:token|secret|api[_-]?key|password)\s+([a-zA-Z0-9\-_.]+)", re.IGNORECASE),
    re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), # Credit card
]

def sanitize_text(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = str(text)
    for p in SENSITIVE_VALUE_PATTERNS:
        cleaned = p.sub("[REDACTED_SECRET]", cleaned)
    # Redact common key-value pairings in free-form text or exception strings
    for k_pat in SENSITIVE_KEY_PATTERNS:
        cleaned = re.sub(
            rf"({k_pat.pattern}\s*[:=]\s*['\"]?)[^\s,'\"}}\]]+",
            r"\1[REDACTED_SECRET]",
            cleaned,
            flags=re.IGNORECASE
        )
    return cleaned

def sanitize_value(key: str, val: Any) -> Any:
    # Check key name
    if any(p.search(key) for p in SENSITIVE_KEY_PATTERNS):
        return "[REDACTED_SECRET]"

    if isinstance(val, str):
        return sanitize_text(val)

    elif isinstance(val, dict):
        return sanitize_dict(val)

    elif isinstance(val, list):
        return [sanitize_value(f"{key}[{i}]", item) for i, item in enumerate(val)]

    return val

def sanitize_dict(data: dict[str, Any], max_depth: int = 5) -> dict[str, Any]:
    if max_depth <= 0 or not isinstance(data, dict):
        return {"_truncated": "Max depth exceeded"}

    sanitized = {}
    for k, v in data.items():
        sanitized[k] = sanitize_value(k, v)
    return sanitized
