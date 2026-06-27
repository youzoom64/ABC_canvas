# powan_id: node-84ee3ba633
# title: モジュール名表示
# parent: node-0b0c56f7ad
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def display_module_name(record: Any) -> str:
    """logging record風の値から、人が追いやすいモジュール名またはファイル名を返す。"""
    for key in ("module", "pathname", "filename", "name"):
        value = _read_value(record, key)
        text = _clean_module_text(value)
        if text:
            return text
    return "<module>"


def _read_value(record: Any, key: str) -> Any:
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


def _clean_module_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = text.replace("\\", "/").rstrip("/")
    if not normalized:
        return ""
    if "/" in normalized:
        return Path(normalized).name or ""
    return normalized
