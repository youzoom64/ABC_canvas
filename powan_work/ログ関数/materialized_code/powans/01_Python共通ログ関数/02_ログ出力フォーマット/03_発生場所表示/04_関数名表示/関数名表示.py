# powan_id: node-f121c07f32
# title: 関数名表示
# parent: node-0b0c56f7ad
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any, Mapping


def display_function_name(record_or_name: Any) -> str:
    """Return a readable function name for a logging record or raw name."""
    value = _read_function_value(record_or_name)
    text = str(value or '').strip()
    return text or '<module>'


def _read_function_value(record_or_name: Any) -> Any:
    if isinstance(record_or_name, Mapping):
        return record_or_name.get('funcName') or record_or_name.get('function')
    if isinstance(record_or_name, str) or record_or_name is None:
        return record_or_name
    return getattr(record_or_name, 'funcName', None) or getattr(record_or_name, 'function', None)
