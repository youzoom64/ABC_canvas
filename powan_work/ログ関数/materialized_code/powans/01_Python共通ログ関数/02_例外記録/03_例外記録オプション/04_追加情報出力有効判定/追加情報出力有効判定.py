# powan_id: node-af09b94563
# title: 追加情報出力有効判定
# parent: node-d20af7cf06
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any

_FALSE_TEXTS = {"0", "false", "f", "no", "n", "off", "disable", "disabled"}
_TRUE_TEXTS = {"1", "true", "t", "yes", "y", "on", "enable", "enabled"}


def _coerce_bool(value: Any, *, default: bool) -> bool:
    """Convert common option values into a predictable boolean."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_TEXTS:
            return True
        if normalized in _FALSE_TEXTS:
            return False
        return default
    return bool(value)


def should_include_context(options: Any = None, *, default: bool = True) -> bool:
    """Decide whether caller-supplied context should be included in exception logs.

    The function accepts the normalized options object used by the parent powan,
    a plain mapping, or any object exposing an ``include_context`` attribute.
    Missing or unrecognized values fall back to ``default`` so logging callers can
    safely opt in or out without raising during exception handling.
    """
    if options is None:
        return default

    if isinstance(options, dict):
        raw_value = options.get("include_context", default)
    else:
        raw_value = getattr(options, "include_context", default)

    return _coerce_bool(raw_value, default=default)
