# powan_id: node-c81fb2773f
# title: フォーマッタ適用
# parent: node-37cb41da55
# powanKind: organ
# codeLanguage: python

"""Apply an already selected formatter to a console handler."""

from __future__ import annotations

import logging


def apply_formatter(
    handler: logging.Handler,
    formatter: logging.Formatter,
) -> logging.Handler:
    """Set ``formatter`` on ``handler`` and return the same handler."""
    handler.setFormatter(formatter)
    return handler


__all__ = ["apply_formatter"]
