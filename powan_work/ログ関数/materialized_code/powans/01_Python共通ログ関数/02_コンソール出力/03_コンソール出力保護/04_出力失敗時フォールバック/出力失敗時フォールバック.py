# powan_id: node-494a2ce8b3
# title: 出力失敗時フォールバック
# parent: node-237b353b32
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import sys
from typing import TextIO


def fallback_console_output_failure(exc: BaseException, *, stream: TextIO | None = None) -> None:
    """Report console-output setup failure without raising another exception.

    This organ powan is intentionally tiny and defensive: it is called only after
    console logging setup has already failed, so every fallback step must be
    best-effort and must never interrupt the application startup path.
    """
    target = stream if stream is not None else sys.stderr
    try:
        target.write(f"logging console setup skipped: {exc}\n")
        flush = getattr(target, "flush", None)
        if callable(flush):
            flush()
    except Exception:
        pass


__all__ = ["fallback_console_output_failure"]
