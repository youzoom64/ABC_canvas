# powan_id: node-7463dd9b1c
# title: ハンドラレベル適用
# parent: node-37cb41da55
# powanKind: organ
# codeLanguage: python

"""Apply a logging level to a console StreamHandler."""

from __future__ import annotations

import logging


def apply_handler_level(
    handler: logging.Handler,
    level: int | str | None,
    *,
    default: int = logging.INFO,
) -> logging.Handler:
    """Set ``handler`` to the resolved logging level and return it."""
    resolved = default if level is None else level
    handler.setLevel(resolved)
    return handler


__all__ = ["apply_handler_level"]
