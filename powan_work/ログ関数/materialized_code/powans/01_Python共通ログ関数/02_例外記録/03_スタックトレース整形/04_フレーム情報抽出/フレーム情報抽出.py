# powan_id: node-86c2f5d7c5
# title: フレーム情報抽出
# parent: node-3d1cd44337
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import traceback
from types import TracebackType
from typing import Any


def extract_frames(tb: TracebackType | None, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Extract frame facts from a traceback."""
    if tb is None:
        return []
    return [
        {"filename": f.filename, "line_number": f.lineno, "function": f.name, "line": f.line or ""}
        for f in traceback.extract_tb(tb, limit=limit)
    ]
