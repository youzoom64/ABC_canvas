# powan_id: node-3d1cd44337
# title: スタックトレース整形
# parent: node-76c5714ad9
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

import traceback
from types import TracebackType


def format_exception_trace(exc: BaseException, *, limit: int | None = None, include_chain: bool = True) -> str:
    """Format an exception traceback for readable logs."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=limit, chain=include_chain)).rstrip()


def format_traceback(tb: TracebackType | None, *, limit: int | None = None) -> str:
    """Format a raw traceback object."""
    if tb is None:
        return ""
    return "".join(traceback.format_tb(tb, limit=limit)).rstrip()
