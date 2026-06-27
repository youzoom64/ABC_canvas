# powan_id: node-a5c623478f
# title: traceback取得
# parent: node-3d1cd44337
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import sys
from types import TracebackType


def get_traceback(exc: BaseException | None = None) -> TracebackType | None:
    """Return the traceback from an exception or the active exception."""
    if exc is not None:
        return exc.__traceback__
    return sys.exc_info()[2]
