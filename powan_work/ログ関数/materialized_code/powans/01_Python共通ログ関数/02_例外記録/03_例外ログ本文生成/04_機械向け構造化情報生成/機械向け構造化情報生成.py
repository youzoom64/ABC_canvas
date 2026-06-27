# powan_id: node-ff3726114e
# title: 機械向け構造化情報生成
# parent: node-661f21f41b
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any


def structured_exception_record(level: str, message: str, exc_info: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a dictionary suitable for JSON logs or external sinks."""
    return {"level": level.upper(), "message": message, "exception": dict(exc_info), "context": dict(context or {})}
