# powan_id: node-2a9653b7a6
# title: 人間向け本文生成
# parent: node-661f21f41b
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any


def human_exception_message(prefix: str, exc_info: dict[str, Any], *, location: str = "") -> str:
    """Create a readable one- or two-line exception summary."""
    text = f"{prefix}: {exc_info.get('type', 'Exception')}: {exc_info.get('message', '')}".rstrip()
    if location:
        text += f" at {location}"
    return text
