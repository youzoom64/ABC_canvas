# powan_id: node-5a978bb4e9
# title: 標準ハンドラーを作る
# parent: node-894cbd722f
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

COMMON_HANDLER_ATTR: Final[str] = "_abc_common_log_handler"
STANDARD_HANDLER_ATTR: Final[str] = "_powan_standard_handler"
DEFAULT_COMMON_HANDLER_NAME: Final[str] = "abc_common_log_handler"
DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def create_standard_handlers(
    app_name: str,
    *,
    file_path: str | Path | None = None,
    level: int = logging.INFO,
    stream=None,
    encoding: str = "utf-8",
) -> list[logging.Handler]:
    """Create common-format handlers for the logger acquisition entry.

    Console output is the default route. When file_path is supplied, a file
    handler is created with the same formatter. The handlers carry stable names
    and marker attributes so sibling duplicate-prevention code can identify
    standard handlers without importing this powan.
    """
    logger_name = _normalize_app_name(app_name)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    console_handler = logging.StreamHandler(stream)
    _configure_standard_handler(
        console_handler,
        formatter=formatter,
        level=level,
        handler_name=DEFAULT_COMMON_HANDLER_NAME,
        handler_kind="console",
        app_name=logger_name,
        log_path=None,
    )

    handlers: list[logging.Handler] = [console_handler]

    if file_path is not None:
        resolved_path = Path(file_path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(resolved_path, encoding=encoding)
        _configure_standard_handler(
            file_handler,
            formatter=formatter,
            level=level,
            handler_name=f"{DEFAULT_COMMON_HANDLER_NAME}.file.{logger_name}",
            handler_kind="file",
            app_name=logger_name,
            log_path=resolved_path,
        )
        handlers.append(file_handler)

    return handlers


def is_standard_handler(
    handler: logging.Handler,
    *,
    app_name: str | None = None,
    kind: str | None = None,
) -> bool:
    """Return True when handler was created by create_standard_handlers."""
    if not isinstance(handler, logging.Handler):
        return False
    if not getattr(handler, STANDARD_HANDLER_ATTR, False):
        return False
    if app_name is not None and getattr(handler, "powan_app_name", None) != _normalize_app_name(app_name):
        return False
    if kind is not None and getattr(handler, "powan_handler_kind", None) != kind:
        return False
    return True


def _normalize_app_name(app_name: str) -> str:
    if not isinstance(app_name, str):
        raise TypeError("app_name must be a string")
    normalized = app_name.strip()
    if not normalized:
        raise ValueError("app_name must be a non-empty string")
    return normalized


def _configure_standard_handler(
    handler: logging.Handler,
    *,
    formatter: logging.Formatter,
    level: int,
    handler_name: str,
    handler_kind: str,
    app_name: str,
    log_path: Path | None,
) -> None:
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.set_name(handler_name)
    setattr(handler, STANDARD_HANDLER_ATTR, True)
    setattr(handler, COMMON_HANDLER_ATTR, True)
    handler.powan_handler_kind = handler_kind
    handler.powan_app_name = app_name
    if log_path is not None:
        handler.powan_log_path = str(log_path)


__all__ = [
    "COMMON_HANDLER_ATTR",
    "STANDARD_HANDLER_ATTR",
    "DEFAULT_COMMON_HANDLER_NAME",
    "DEFAULT_LOG_FORMAT",
    "DEFAULT_DATE_FORMAT",
    "create_standard_handlers",
    "is_standard_handler",
]
