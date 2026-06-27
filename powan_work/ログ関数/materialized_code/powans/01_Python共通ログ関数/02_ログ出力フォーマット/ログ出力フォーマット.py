# powan_id: node-c6a89ade0d
# title: ログ出力フォーマット
# parent: node-704b909f82
# powanKind:
# codeLanguage: python

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(app_name)s | %(name)s:%(lineno)d | %(message)s"
DETAIL_FORMAT = "%(asctime)s | %(levelname)-8s | %(app_name)s | %(process)d:%(threadName)s | %(name)s.%(funcName)s:%(lineno)d | %(message)s"
SIMPLE_FORMAT = "%(levelname)-8s | %(message)s"


@dataclass(frozen=True)
class LogOutputFormatOptions:
    """Readable log-output format settings shared by console and file handlers."""

    app_name: str = "app"
    style: str = "normal"
    datefmt: str = DEFAULT_DATE_FORMAT
    include_location: bool = True
    include_app: bool = True


class AppNameFilter(logging.Filter):
    """Ensure every LogRecord has the app_name field used by the formatter."""

    def __init__(self, app_name: str) -> None:
        super().__init__()
        self.app_name = app_name or "app"

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "app_name") or not getattr(record, "app_name"):
            record.app_name = self.app_name
        return True


class ReadableLogFormatter(logging.Formatter):
    """Formatter that keeps time, level, app, location, and message scan-friendly."""

    default_msec_format = "%s.%03d"

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "app_name") or not getattr(record, "app_name"):
            record.app_name = "app"
        record.levelname = str(record.levelname).upper()
        return super().format(record)


def build_format_string(options: LogOutputFormatOptions | Mapping[str, Any] | None = None) -> str:
    """Build a logging format string from this powan's display meaning."""

    opts = normalize_options(options)
    if opts.style == "simple":
        return SIMPLE_FORMAT
    if opts.style == "detail":
        return DETAIL_FORMAT

    parts: list[str] = ["%(asctime)s", "%(levelname)-8s"]
    if opts.include_app:
        parts.append("%(app_name)s")
    if opts.include_location:
        parts.append("%(name)s:%(lineno)d")
    parts.append("%(message)s")
    return " | ".join(parts)


def create_readable_formatter(options: LogOutputFormatOptions | Mapping[str, Any] | None = None) -> ReadableLogFormatter:
    """Create the standard formatter used by common Python logging handlers."""

    opts = normalize_options(options)
    return ReadableLogFormatter(build_format_string(opts), datefmt=opts.datefmt)


def attach_format_to_handler(
    handler: logging.Handler,
    options: LogOutputFormatOptions | Mapping[str, Any] | None = None,
) -> logging.Handler:
    """Attach formatter and app-name filter to a handler, then return it."""

    opts = normalize_options(options)
    handler.setFormatter(create_readable_formatter(opts))
    handler.addFilter(AppNameFilter(opts.app_name))
    return handler


def format_record_preview(record_values: Mapping[str, Any], options: LogOutputFormatOptions | Mapping[str, Any] | None = None) -> str:
    """Format a dict-like record preview without requiring a live Logger."""

    opts = normalize_options(options)
    record = logging.LogRecord(
        name=str(record_values.get("name", "preview")),
        level=int(record_values.get("levelno", logging.INFO)),
        pathname=str(record_values.get("pathname", record_values.get("name", "preview"))),
        lineno=int(record_values.get("lineno", 0) or 0),
        msg=str(record_values.get("message", record_values.get("msg", ""))),
        args=(),
        exc_info=None,
    )
    record.app_name = str(record_values.get("app_name", opts.app_name) or opts.app_name)
    record.funcName = str(record_values.get("funcName", record_values.get("function", "<module>")))
    created = record_values.get("created")
    if isinstance(created, (int, float)):
        record.created = float(created)
    elif isinstance(created, datetime):
        record.created = created.timestamp()
    return create_readable_formatter(opts).format(record)


def normalize_options(options: LogOutputFormatOptions | Mapping[str, Any] | None = None) -> LogOutputFormatOptions:
    """Normalize loose settings into LogOutputFormatOptions."""

    if isinstance(options, LogOutputFormatOptions):
        return options
    source = dict(options or {})
    style = str(source.get("style", source.get("format", "normal"))).strip().lower()
    if style not in {"simple", "normal", "detail"}:
        raise ValueError(f"unknown log output format style: {style!r}")
    return LogOutputFormatOptions(
        app_name=str(source.get("app_name", source.get("appName", "app")) or "app"),
        style=style,
        datefmt=str(source.get("datefmt", source.get("date_format", DEFAULT_DATE_FORMAT)) or DEFAULT_DATE_FORMAT),
        include_location=bool(source.get("include_location", source.get("includeLocation", True))),
        include_app=bool(source.get("include_app", source.get("includeApp", True))),
    )


__all__ = [
    "AppNameFilter",
    "LogOutputFormatOptions",
    "ReadableLogFormatter",
    "attach_format_to_handler",
    "build_format_string",
    "create_readable_formatter",
    "format_record_preview",
    "normalize_options",
]
