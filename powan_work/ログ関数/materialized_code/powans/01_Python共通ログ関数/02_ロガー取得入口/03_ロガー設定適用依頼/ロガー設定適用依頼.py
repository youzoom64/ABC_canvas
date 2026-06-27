# powan_id: node-4e907d218e
# title: ロガー設定適用依頼
# parent: node-894cbd722f
# powanKind: nerve
# codeLanguage: python

import logging
from collections.abc import Iterable

CONFIGURED_MARK = "_common_logger_configured"
COMMON_HANDLER_MARK = "_common_logger_handler"
COMMON_HANDLER_KEY = "_common_logger_handler_key"


def configure_logger(
    logger: logging.Logger,
    handlers: logging.Handler | Iterable[logging.Handler] | None,
    *,
    level: int = logging.INFO,
    propagate: bool = False,
) -> logging.Logger:
    """Apply prepared handlers and settings to a logger, then return it."""
    prepared_handlers = normalize_handlers(handlers)
    apply_level(logger, prepared_handlers, level)
    add_handlers(logger, prepared_handlers)
    control_propagate(logger, propagate)
    mark_configured(logger)
    return logger


def normalize_handlers(
    handlers: logging.Handler | Iterable[logging.Handler] | None,
) -> tuple[logging.Handler, ...]:
    """Normalize prepared handler input without creating new handlers."""
    if handlers is None:
        return ()
    if isinstance(handlers, logging.Handler):
        return (handlers,)
    if isinstance(handlers, Iterable):
        normalized = tuple(handlers)
        for handler in normalized:
            if not isinstance(handler, logging.Handler):
                raise TypeError("handlers must contain logging.Handler instances")
        return normalized
    raise TypeError("handlers must be a logging.Handler, an iterable of handlers, or None")


def apply_level(
    logger: logging.Logger,
    handlers: Iterable[logging.Handler],
    level: int,
) -> logging.Logger:
    """Apply the same standard logging level to the logger and prepared handlers."""
    logger.setLevel(level)
    for handler in handlers:
        handler.setLevel(level)
    return logger


def add_handlers(
    logger: logging.Logger,
    handlers: Iterable[logging.Handler],
) -> logging.Logger:
    """Attach prepared common handlers while avoiding duplicate common output."""
    for handler in handlers:
        setattr(handler, COMMON_HANDLER_MARK, True)
        if not has_equivalent_common_handler(logger, handler):
            logger.addHandler(handler)
    return logger


def has_equivalent_common_handler(logger: logging.Logger, handler: logging.Handler) -> bool:
    """Return True when logger already owns this prepared common handler."""
    incoming_key = getattr(handler, COMMON_HANDLER_KEY, None)
    for existing in logger.handlers:
        if existing is handler:
            return True
        if (
            incoming_key is not None
            and getattr(existing, COMMON_HANDLER_MARK, False)
            and getattr(existing, COMMON_HANDLER_KEY, None) == incoming_key
        ):
            return True
    return False


def control_propagate(logger: logging.Logger, propagate: bool) -> logging.Logger:
    """Control propagation so configured logger output does not duplicate upstream."""
    logger.propagate = bool(propagate)
    return logger


def mark_configured(logger: logging.Logger) -> logging.Logger:
    """Mark the logger as configured by the common logging entrypoint."""
    setattr(logger, CONFIGURED_MARK, True)
    return logger


def is_configured(logger: logging.Logger) -> bool:
    """Return whether this logger has already received the common entrypoint setup."""
    return bool(getattr(logger, CONFIGURED_MARK, False))


add_handlers_once = add_handlers
set_logger_propagate = control_propagate
mark_logger_configured = mark_configured
