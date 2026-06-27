# powan_id: node-8223ad544a
# title: ロガーへ設定を適用する
# parent: node-894cbd722f
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import Final

_CONFIGURED_ATTR: Final[str] = "_abc_common_logger_configured"
_COMMON_HANDLER_ATTR: Final[str] = "_abc_common_log_handler"
_DEFAULT_HANDLER_NAME: Final[str] = "abc_common_log_handler"


def apply_logger_config(
    logger: logging.Logger,
    handlers: logging.Handler | Iterable[logging.Handler],
    *,
    level: int = logging.INFO,
    formatter: logging.Formatter | None = None,
    propagate: bool = False,
    configured_attr: str = _CONFIGURED_ATTR,
    handler_marker_attr: str = _COMMON_HANDLER_ATTR,
    default_handler_name: str = _DEFAULT_HANDLER_NAME,
) -> logging.Logger:
    """Apply shared logging settings to a logger and return it.

    This organ only assembles already-created pieces: level, handlers, optional
    formatter, propagation, and the configured marker. Duplicate prevention is
    based on stable handler names and the common marker so sibling powans can
    share the same contract without importing each other.
    """
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger")

    logger.setLevel(level)
    logger.propagate = propagate

    for index, handler in enumerate(_normalize_handlers(handlers)):
        handler.setLevel(level)
        if formatter is not None:
            handler.setFormatter(formatter)
        _add_common_handler_once(
            logger,
            handler,
            marker_attr=handler_marker_attr,
            fallback_name=_fallback_handler_name(default_handler_name, index),
        )

    setattr(logger, configured_attr, True)
    return logger


def is_logger_configured(
    logger: logging.Logger,
    *,
    configured_attr: str = _CONFIGURED_ATTR,
) -> bool:
    """Return True when shared logger settings were already applied."""
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger")
    return bool(getattr(logger, configured_attr, False))


def _normalize_handlers(
    handlers: logging.Handler | Iterable[logging.Handler],
) -> tuple[logging.Handler, ...]:
    if isinstance(handlers, logging.Handler):
        return (handlers,)

    normalized = tuple(handlers)
    for handler in normalized:
        if not isinstance(handler, logging.Handler):
            raise TypeError("handlers must contain only logging.Handler instances")
    return normalized


def _add_common_handler_once(
    logger: logging.Logger,
    handler: logging.Handler,
    *,
    marker_attr: str,
    fallback_name: str,
) -> bool:
    if not handler.get_name():
        handler.set_name(fallback_name)

    if _has_equivalent_handler(logger, handler, marker_attr=marker_attr):
        return False

    setattr(handler, marker_attr, True)
    logger.addHandler(handler)
    return True


def _has_equivalent_handler(
    logger: logging.Logger,
    candidate: logging.Handler,
    *,
    marker_attr: str,
) -> bool:
    candidate_name = candidate.get_name()
    for existing in logger.handlers:
        if existing is candidate:
            return True
        if candidate_name and existing.get_name() == candidate_name:
            return True
        if (
            candidate_name
            and getattr(existing, marker_attr, False)
            and existing.get_name() == candidate_name
        ):
            return True
    return False


def _fallback_handler_name(base_name: str, index: int) -> str:
    if index == 0:
        return base_name
    return f"{base_name}.{index + 1}"


__all__ = ["apply_logger_config", "is_logger_configured"]
