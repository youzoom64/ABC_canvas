# powan_id: node-0d90fc67c6
# title: マスク対象キー判定
# parent: node-ebfdc1918d
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
)


def normalize_context_key(key: object) -> str:
    """Return a normalized key string for secret-key checks."""
    return str(key).strip().lower().replace("-", "_")


def is_sensitive_key(key: object) -> bool:
    """Return True when a context key should not be logged raw."""
    text = normalize_context_key(key)
    return any(part in text for part in SENSITIVE_KEY_PARTS)
