# powan_id: node-894cbd722f
# title: ロガー取得入口
# parent: node-704b909f82
# powanKind:
# codeLanguage: python

from __future__ import annotations

from collections.abc import Iterable
import logging
from pathlib import Path
from typing import Final, TextIO

CONFIGURED_ATTR: Final[str] = "_abc_common_logger_configured"
COMMON_HANDLER_ATTR: Final[str] = "_abc_common_log_handler"
DEFAULT_HANDLER_NAME: Final[str] = "abc_common_log_handler"
DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def get_logger(
    app_name: str,
    *,
    level: int = logging.INFO,
    file_path: str | Path | None = None,
    stream: TextIO | None = None,
    encoding: str = "utf-8",
    propagate: bool = False,
) -> logging.Logger:
    """Return a shared, configured logger for an application name.

    Callers only need get_logger(app_name) to start logging. The function is
    idempotent: repeated calls for the same app return the same logger without
    adding duplicate handlers. Console output is enabled by default, and an
    optional file_path adds file output with the same formatter.
    """
    logger_name = _normalize_logger_name(app_name)
    logger = logging.getLogger(logger_name)

    if _is_logger_configured(logger):
        return logger

    handlers = _create_standard_handlers(
        logger_name,
        file_path=file_path,
        level=level,
        stream=stream,
        encoding=encoding,
    )
    _configure_logger(
        logger,
        handlers,
        level=level,
        propagate=propagate,
    )
    return logger


def _normalize_logger_name(app_name: str) -> str:
    if app_name is None:
        raise ValueError("app_name is required and cannot be None")
    if not isinstance(app_name, str):
        raise TypeError("app_name must be a string")

    logger_name = app_name.strip()
    if not logger_name:
        raise ValueError("app_name must not be empty or whitespace only")
    return logger_name


def _is_logger_configured(logger: logging.Logger) -> bool:
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger")
    return bool(getattr(logger, CONFIGURED_ATTR, False))


def _create_standard_handlers(
    logger_name: str,
    *,
    file_path: str | Path | None,
    level: int,
    stream: TextIO | None,
    encoding: str,
) -> tuple[logging.Handler, ...]:
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    console_handler = logging.StreamHandler(stream)
    _prepare_handler(
        console_handler,
        level=level,
        formatter=formatter,
        name=DEFAULT_HANDLER_NAME,
    )

    handlers: list[logging.Handler] = [console_handler]

    if file_path is not None:
        resolved_path = Path(file_path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(resolved_path, encoding=encoding)
        _prepare_handler(
            file_handler,
            level=level,
            formatter=formatter,
            name=f"{DEFAULT_HANDLER_NAME}.file.{logger_name}",
        )
        handlers.append(file_handler)

    return tuple(handlers)


def _prepare_handler(
    handler: logging.Handler,
    *,
    level: int,
    formatter: logging.Formatter,
    name: str,
) -> logging.Handler:
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.set_name(name)
    setattr(handler, COMMON_HANDLER_ATTR, True)
    return handler


def _configure_logger(
    logger: logging.Logger,
    handlers: logging.Handler | Iterable[logging.Handler],
    *,
    level: int,
    propagate: bool,
) -> logging.Logger:
    logger.setLevel(level)
    logger.propagate = bool(propagate)

    for handler in _normalize_handlers(handlers):
        _add_handler_once(logger, handler)

    setattr(logger, CONFIGURED_ATTR, True)
    return logger


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


def _add_handler_once(logger: logging.Logger, handler: logging.Handler) -> bool:
    handler_name = handler.get_name()
    for existing in logger.handlers:
        if existing is handler:
            return False
        if handler_name and existing.get_name() == handler_name:
            return False
        if getattr(existing, COMMON_HANDLER_ATTR, False) and handler_name and existing.get_name() == handler_name:
            return False

    logger.addHandler(handler)
    return True


__all__ = ["get_logger"]
