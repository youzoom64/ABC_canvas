# powan_id: node-294998669d
# title: ハンドラー追加
# parent: node-4e907d218e
# powanKind: organ
# codeLanguage: python

import logging
from collections.abc import Iterable
from typing import Any


def add_handlers_once(
    logger: logging.Logger,
    handlers: Iterable[logging.Handler],
    marker_attr: str = "_abc_common_log_handler",
) -> logging.Logger:
    """Add handlers to logger once, avoiding duplicate logging output."""
    for handler in handlers:
        setattr(handler, marker_attr, True)
        if not has_equivalent_handler(logger, handler, marker_attr):
            logger.addHandler(handler)
    return logger


def has_equivalent_handler(
    logger: logging.Logger,
    handler: logging.Handler,
    marker_attr: str = "_abc_common_log_handler",
) -> bool:
    """Return True when logger already has the same instance, name, or marked handler."""
    incoming_name = _handler_name(handler)
    incoming_identity = _handler_identity(handler)

    for existing in logger.handlers:
        if existing is handler:
            return True

        existing_name = _handler_name(existing)
        if incoming_name is not None and existing_name == incoming_name:
            return True

        if (
            getattr(existing, marker_attr, False)
            and getattr(handler, marker_attr, False)
            and _handler_identity(existing) == incoming_identity
        ):
            return True

    return False


def _handler_name(handler: logging.Handler) -> str | None:
    """Return a useful handler name when one was explicitly assigned."""
    name = getattr(handler, "name", None)
    return name or None


def _handler_identity(handler: logging.Handler) -> tuple[type[logging.Handler], Any]:
    """Build a stable identity for marked common handlers using standard logging fields."""
    filename = getattr(handler, "baseFilename", None)
    if filename is not None:
        return (type(handler), filename)

    stream = getattr(handler, "stream", None)
    if stream is not None:
        return (type(handler), id(stream))

    return (type(handler), _handler_name(handler))


add_handlers = add_handlers_once
