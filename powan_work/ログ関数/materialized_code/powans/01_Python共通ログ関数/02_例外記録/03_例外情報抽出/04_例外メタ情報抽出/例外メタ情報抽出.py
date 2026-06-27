# powan_id: node-3079240749
# title: 例外メタ情報抽出
# parent: node-efe6206313
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any


def exception_metadata(exc: BaseException, allowed_attrs: tuple[str, ...] = ()) -> dict[str, Any]:
    """Extract selected public attributes from an exception."""
    result: dict[str, Any] = {}
    for name in allowed_attrs:
        if name.startswith("_"):
            continue
        if hasattr(exc, name):
            value = getattr(exc, name)
            result[name] = repr(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
    return result
