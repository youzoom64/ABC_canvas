# powan_id: node-ebfdc1918d
# title: 機密情報マスク方針
# parent: node-d20af7cf06
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
)


def is_sensitive_key(key: str) -> bool:
    """Return True when a context key should not be logged raw."""
    text = str(key).lower().replace("-", "_")
    return any(part in text for part in SENSITIVE_KEY_PARTS)


def mask_value(value: Any, *, replacement: str = "***", max_length: int = 200) -> str:
    """Return a log-safe string for a sensitive or very long value."""
    if value is None:
        return ""

    text = str(value)
    if not text:
        return text
    if len(text) > max_length:
        return text[:max_length] + "..."
    return replacement


def render_context_value(value: Any, *, max_length: int = 200) -> Any:
    """Return a non-secret value, shortening long strings for compact logs."""
    if value is None:
        return ""

    text = str(value)
    if len(text) > max_length:
        return text[:max_length] + "..."
    return value


def mask_context(
    context: Mapping[str, Any] | None,
    *,
    replacement: str = "***",
    max_length: int = 200,
) -> dict[str, Any]:
    """Return a copy of context with secret-looking fields masked for logs."""
    if not context:
        return {}

    masked: dict[str, Any] = {}
    for key, value in context.items():
        if is_sensitive_key(str(key)):
            masked[str(key)] = mask_value(value, replacement=replacement, max_length=max_length)
        else:
            masked[str(key)] = render_context_value(value, max_length=max_length)
    return masked
