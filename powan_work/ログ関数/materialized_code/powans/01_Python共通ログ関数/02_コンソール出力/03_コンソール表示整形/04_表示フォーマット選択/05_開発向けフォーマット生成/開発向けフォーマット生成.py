# powan_id: node-0f5e6619d0
# title: 開発向けフォーマット生成
# parent: node-14cf6a99bc
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class DevelopmentLogFields:
    """Normalized fields used by the development console format."""

    timestamp: str
    level: str
    logger_name: str
    location: str
    message: str


DEFAULT_DEVELOPMENT_TEMPLATE = "{timestamp} [{level}] {logger_name} {location}: {message}"


def _value(source: Mapping[str, Any], *names: str, default: Any = "") -> Any:
    for name in names:
        value = source.get(name)
        if value is not None and value != "":
            return value
    return default


def _format_timestamp(value: Any = None) -> str:
    if value is None or value == "":
        value = datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return str(value)


def _format_location(source: Mapping[str, Any]) -> str:
    explicit = _value(source, "location", "source", default="")
    if explicit:
        return str(explicit)

    pathname = _value(source, "pathname", "file", "filename", default="")
    line = _value(source, "lineno", "line", default="")
    function = _value(source, "funcName", "function", "func", default="")

    parts: list[str] = []
    if pathname:
        parts.append(Path(str(pathname)).name)
    if line:
        if parts:
            parts[-1] = f"{parts[-1]}:{line}"
        else:
            parts.append(f"line:{line}")
    if function:
        parts.append(f"in {function}")

    return " ".join(parts) if parts else "unknown"


def build_development_fields(record: Mapping[str, Any] | None = None, **overrides: Any) -> DevelopmentLogFields:
    """Return normalized fields for a development-oriented log line."""
    source = {**dict(record or {}), **overrides}
    return DevelopmentLogFields(
        timestamp=_format_timestamp(_value(source, "timestamp", "created_at", "time", default=None)),
        level=str(_value(source, "level", "levelname", "severity", default="INFO")).upper(),
        logger_name=str(_value(source, "logger_name", "name", "logger", default="root")),
        location=_format_location(source),
        message=str(_value(source, "message", "msg", default="")),
    )


def development_format_template(*, include_timestamp: bool = True, include_location: bool = True) -> str:
    """Return the template for development console output."""
    prefix = "{timestamp} [{level}] {logger_name}" if include_timestamp else "[{level}] {logger_name}"
    location = " {location}" if include_location else ""
    return f"{prefix}{location}: {{message}}"


def format_development_log(record: Mapping[str, Any] | None = None, *, template: str | None = None, **overrides: Any) -> str:
    """Generate a developer-friendly line with time, level, logger, location, and message."""
    fields = build_development_fields(record, **overrides)
    return (template or DEFAULT_DEVELOPMENT_TEMPLATE).format(
        timestamp=fields.timestamp,
        level=fields.level,
        logger_name=fields.logger_name,
        name=fields.logger_name,
        location=fields.location,
        message=fields.message,
    )


def generate_development_format(record: Mapping[str, Any] | None = None, **overrides: Any) -> str:
    """Compatibility wrapper for this powan's main responsibility."""
    return format_development_log(record, **overrides)


__all__ = [
    "DEFAULT_DEVELOPMENT_TEMPLATE",
    "DevelopmentLogFields",
    "build_development_fields",
    "development_format_template",
    "format_development_log",
    "generate_development_format",
]
