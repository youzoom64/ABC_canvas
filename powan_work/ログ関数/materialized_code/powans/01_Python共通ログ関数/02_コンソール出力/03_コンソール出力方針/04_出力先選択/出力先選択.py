# powan_id: node-f104ac0f96
# title: 出力先選択
# parent: node-ffda89edb6
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import sys
from typing import Any, Mapping, TextIO

_STDERR_LEVELS = {"WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"}


def select_console_stream(
    level: str = "INFO",
    config: Mapping[str, Any] | None = None,
) -> tuple[str, TextIO]:
    """Choose stdout or stderr for a console log event."""

    cfg = config or {}
    configured = str(cfg.get("stream", "")).strip().lower()
    if configured in {"stdout", "out"}:
        return "stdout", sys.stdout
    if configured in {"stderr", "err"}:
        return "stderr", sys.stderr

    normalized_level = str(level or "INFO").strip().upper()
    if normalized_level in _STDERR_LEVELS:
        return "stderr", sys.stderr
    return "stdout", sys.stdout
