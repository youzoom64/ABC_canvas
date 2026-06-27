# powan_id: node-250dd8dd18
# title: スタック出力有効判定
# parent: node-d20af7cf06
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any

_TRUE_STRINGS = {"1", "true", "yes", "on", "y", "t"}
_FALSE_STRINGS = {"0", "false", "no", "off", "n", "f"}
_MISSING = object()


def _coerce_bool(value: Any, default: bool) -> bool:
    """Convert common option values into a bool without raising on odd input."""
    if value is _MISSING or value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True
        if normalized in _FALSE_STRINGS:
            return False
        if normalized == "":
            return bool(default)
    return bool(value)


def _read_include_stack(options: Any) -> Any:
    """Read include_stack from dict-like or attribute-style options."""
    if options is None:
        return _MISSING
    if isinstance(options, dict):
        return options.get("include_stack", _MISSING)
    return getattr(options, "include_stack", _MISSING)


def should_include_stack(options: Any = None, *, include_stack: Any = _MISSING, default: bool = True) -> bool:
    """Decide whether exception log output should include traceback text.

    Explicit call arguments take priority over values carried by an options
    object. The function accepts dataclasses, simple objects, mappings, and
    common string flags so it can sit quietly inside shared logging helpers.
    """
    selected = include_stack if include_stack is not _MISSING else _read_include_stack(options)
    return _coerce_bool(selected, default)
