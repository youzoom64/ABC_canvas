# powan_id: node-2a4b80b183
# title: 追加コンテキスト結合
# parent: node-661f21f41b
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any


def merge_exception_context(*contexts: dict[str, Any] | None) -> dict[str, Any]:
    """Merge optional context dictionaries while ignoring None values."""
    merged: dict[str, Any] = {}
    for context in contexts:
        if context:
            merged.update(context)
    return merged
