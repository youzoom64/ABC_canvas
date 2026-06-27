# powan_id: node-b9509c8a49
# title: チェーン出力有効判定
# parent: node-d20af7cf06
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any

_TRUE_TEXTS = {"1", "true", "yes", "on", "include", "enabled"}
_FALSE_TEXTS = {"0", "false", "no", "off", "exclude", "disabled"}


def _coerce_bool(value: Any, *, default: bool) -> bool:
    """Convert common option values to bool without surprising callers."""
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


def should_include_chain(options: Any = None, *, default: bool = True) -> bool:
    """Decide whether exception cause/context chains should be logged.

    The logging option may be supplied as a mapping, an options object, or left
    unset. Only the include_chain field is inspected, keeping this helper small
    and free of side effects for shared logging modules.
    """
    if options is None:
        return bool(default)

    if isinstance(options, dict):
        raw_value = options.get("include_chain", default)
    else:
        raw_value = getattr(options, "include_chain", default)

    return _coerce_bool(raw_value, default=bool(default))
