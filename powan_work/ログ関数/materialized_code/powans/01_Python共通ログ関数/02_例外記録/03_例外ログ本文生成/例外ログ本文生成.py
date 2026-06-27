# powan_id: node-661f21f41b
# title: 例外ログ本文生成
# parent: node-76c5714ad9
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from typing import Any


def build_exception_log_message(message: str, exception_info: dict[str, Any], stack: str = "", context: dict[str, Any] | None = None) -> str:
    """Combine a user message, exception facts, stack text, and context for logging."""
    parts = [message.rstrip()]
    parts.append(f"Exception: {exception_info.get('qualified_type') or exception_info.get('type')}: {exception_info.get('message', '')}")
    if context:
        parts.append("Context: " + ", ".join(f"{k}={v!r}" for k, v in sorted(context.items())))
    if stack:
        parts.append("Traceback:\n" + stack.rstrip())
    return "\n".join(part for part in parts if part)
