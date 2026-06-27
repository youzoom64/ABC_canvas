# powan_id: node-70abfb41d4
# title: 重複ハンドラ判定
# parent: node-237b353b32
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Any


def has_equivalent_stream_handler(logger: logging.Logger, candidate: logging.Handler) -> bool:
    """Return True when logger already has an equivalent StreamHandler.

    Equivalence is intentionally narrow: this guard prevents adding the same
    kind of stream handler to the same output stream twice.  Formatter and
    level differences are not enough to make console output safe to duplicate,
    because two handlers writing to the same stream still produce repeated
    lines.
    """
    if not isinstance(candidate, logging.StreamHandler):
        return False

    candidate_stream = _handler_stream_identity(candidate)
    for existing in logger.handlers:
        if existing is candidate:
            return True
        if not isinstance(existing, logging.StreamHandler):
            continue
        if type(existing) is not type(candidate):
            continue
        if _handler_stream_identity(existing) == candidate_stream:
            return True
    return False


def _handler_stream_identity(handler: logging.StreamHandler[Any]) -> tuple[str, int | None, str | None]:
    stream = getattr(handler, "stream", None)
    if stream is None:
        return ("missing", None, None)

    try:
        fileno = stream.fileno()
    except Exception:
        fileno = None

    name = getattr(stream, "name", None)
    if name is not None:
        name = str(name)

    if fileno is not None:
        return ("fd", int(fileno), name)
    return ("object", id(stream), name)


__all__ = ["has_equivalent_stream_handler"]
