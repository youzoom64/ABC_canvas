# powan_id: node-077ce1f45f
# title: ファイルハンドラ生成
# parent: node-34e4ee95ea
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from logging import Handler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


def _checked_file_handler_level(level: int | str) -> int:
    """Return a logging level integer for a handler."""

    try:
        checked = logging._checkLevel(level)
    except (TypeError, ValueError) as exc:
        raise FileLogConfigError(f"file handler level is invalid: {level!r}") from exc
    if not isinstance(checked, int):
        raise FileLogConfigError(f"file handler level is invalid: {level!r}")
    return checked


def _checked_file_formatter(formatter: logging.Formatter | None) -> logging.Formatter | None:
    """Return formatter after checking the standard logging contract."""

    if formatter is not None and not isinstance(formatter, logging.Formatter):
        raise FileLogConfigError(
            f"file handler formatter must be logging.Formatter or None: {formatter!r}"
        )
    return formatter


def create_file_handler(
    config: FileOutputConfig,
    *,
    level: int | str = logging.INFO,
    formatter: logging.Formatter | None = None,
) -> Handler | None:
    """Create a standard logging file handler from resolved file settings.

    The parent powan resolves enablement, path, rotation, encoding, and delay.
    This organ powan only turns that resolved config into a logging Handler.
    """

    if not config.enabled:
        return None

    handler_level = _checked_file_handler_level(level)
    checked_formatter = _checked_file_formatter(formatter)
    policy = config.rotation

    try:
        if policy.mode == "none":
            handler: Handler = logging.FileHandler(
                config.path,
                encoding=config.encoding,
                delay=config.delay,
            )
        elif policy.mode == "size":
            if policy.max_bytes <= 0:
                raise FileLogConfigError("size-rotating file handler requires max_bytes greater than 0")
            handler = RotatingFileHandler(
                config.path,
                maxBytes=policy.max_bytes,
                backupCount=policy.backup_count,
                encoding=config.encoding,
                delay=config.delay,
            )
        elif policy.mode == "time":
            if policy.interval <= 0:
                raise FileLogConfigError("time-rotating file handler requires interval greater than 0")
            handler = TimedRotatingFileHandler(
                config.path,
                when=policy.when,
                interval=policy.interval,
                backupCount=policy.backup_count,
                encoding=config.encoding,
                delay=config.delay,
                utc=policy.utc,
            )
        else:
            raise FileLogConfigError(f"unknown file handler rotation mode: {policy.mode!r}")
    except OSError as exc:
        raise FileLogConfigError(f"failed to open log file {config.path!s}: {exc}") from exc

    handler.setLevel(handler_level)
    if checked_formatter is not None:
        handler.setFormatter(checked_formatter)
    return handler
