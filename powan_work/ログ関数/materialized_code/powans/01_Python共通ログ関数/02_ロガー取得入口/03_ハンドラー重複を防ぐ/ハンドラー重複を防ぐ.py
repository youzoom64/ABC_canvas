# powan_id: node-ce60d0e976
# title: ハンドラー重複を防ぐ
# parent: node-894cbd722f
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Final

COMMON_HANDLER_ATTR: Final[str] = "_abc_common_log_handler"
DEFAULT_COMMON_HANDLER_NAME: Final[str] = "abc_common_log_handler"


def mark_common_log_handler(
    handler: logging.Handler,
    *,
    handler_name: str = DEFAULT_COMMON_HANDLER_NAME,
    marker_attr: str = COMMON_HANDLER_ATTR,
) -> logging.Handler:
    """Mark handler as a shared common-log handler and return it."""
    if not isinstance(handler, logging.Handler):
        raise TypeError("handler must be a logging.Handler")

    setattr(handler, marker_attr, True)
    if handler_name:
        handler.set_name(handler_name)
    return handler


def is_common_log_handler(
    handler: logging.Handler,
    *,
    handler_name: str = DEFAULT_COMMON_HANDLER_NAME,
    marker_attr: str = COMMON_HANDLER_ATTR,
) -> bool:
    """Return True when handler carries the common-log marker or name."""
    if not isinstance(handler, logging.Handler):
        return False
    return bool(getattr(handler, marker_attr, False)) or (
        bool(handler_name) and handler.get_name() == handler_name
    )


def has_common_log_handler(
    logger: logging.Logger,
    candidate: logging.Handler | None = None,
    *,
    handler_name: str = DEFAULT_COMMON_HANDLER_NAME,
    marker_attr: str = COMMON_HANDLER_ATTR,
) -> bool:
    """Return True when logger already has the shared common-log handler.

    If candidate is supplied, object identity and candidate name are checked too.
    This lets get_logger safely call handler creation every time without growing
    duplicate output lines.
    """
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger")
    if candidate is not None and not isinstance(candidate, logging.Handler):
        raise TypeError("candidate must be a logging.Handler or None")

    candidate_name = candidate.get_name() if candidate is not None else ""
    for existing in logger.handlers:
        if candidate is not None and existing is candidate:
            return True
        if is_common_log_handler(
            existing, handler_name=handler_name, marker_attr=marker_attr
        ):
            return True
        if candidate_name and existing.get_name() == candidate_name:
            return True
    return False


def add_common_log_handler_once(
    logger: logging.Logger,
    handler: logging.Handler,
    *,
    handler_name: str = DEFAULT_COMMON_HANDLER_NAME,
    marker_attr: str = COMMON_HANDLER_ATTR,
) -> bool:
    """Add handler once, returning True only when a new handler was attached."""
    if has_common_log_handler(
        logger,
        handler,
        handler_name=handler_name,
        marker_attr=marker_attr,
    ):
        return False

    mark_common_log_handler(
        handler, handler_name=handler_name, marker_attr=marker_attr
    )
    logger.addHandler(handler)
    return True


__all__ = [
    "COMMON_HANDLER_ATTR",
    "DEFAULT_COMMON_HANDLER_NAME",
    "mark_common_log_handler",
    "is_common_log_handler",
    "has_common_log_handler",
    "add_common_log_handler_once",
]
