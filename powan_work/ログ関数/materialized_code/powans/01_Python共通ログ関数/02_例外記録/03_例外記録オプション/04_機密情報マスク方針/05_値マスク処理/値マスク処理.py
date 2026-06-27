# powan_id: node-e2763a1820
# title: 値マスク処理
# parent: node-ebfdc1918d
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any


def stringify_log_value(value: Any) -> str:
    """Return a stable string representation for log context values."""
    if value is None:
        return ""
    return str(value)


def shorten_value(value: Any, *, max_length: int = 200) -> str:
    """Return a string value shortened for compact log output."""
    text = stringify_log_value(value)
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def mask_value(value: Any, *, replacement: str = "***", max_length: int = 200) -> str:
    """Return a masked or shortened representation for a sensitive value."""
    text = shorten_value(value, max_length=max_length)
    return replacement if text else text
