# powan_id: node-bb37d31635
# title: ハンドラ名設定
# parent: node-37cb41da55
# powanKind: organ
# codeLanguage: python

"""Set a stable identifying name on a logging handler."""

from __future__ import annotations

import logging

DEFAULT_HANDLER_NAME = "console"


def set_handler_name(
    handler: logging.Handler,
    name: str | None = DEFAULT_HANDLER_NAME,
) -> logging.Handler:
    """Set ``handler`` name and return the same handler."""
    handler.set_name(name or DEFAULT_HANDLER_NAME)
    return handler


__all__ = ["DEFAULT_HANDLER_NAME", "set_handler_name"]
