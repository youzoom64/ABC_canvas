# powan_id: node-f66f69bee0
# title: コンソールハンドラ生成
# parent: node-ef620afdd3
# powanKind: organ
# codeLanguage: python

"""Create configured console logging handlers.

This organ powan turns loose console logging settings into a standard
``logging.StreamHandler``. It accepts dictionaries or config-like objects,
returns ``None`` when console output is disabled, and provides a small attach
helper for ``logging.Logger`` setup.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, replace
from typing import Any, Mapping, TextIO


TRACE_LEVEL = 5
DEFAULT_CONSOLE_LEVEL = "INFO"
DEFAULT_CONSOLE_FORMAT = "standard"

_FORMATS: dict[str, str] = {
    "plain": "%(message)s",
    "compact": "%(levelname)s:%(name)s:%(message)s",
    "standard": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    "detail": "%(asctime)s %(levelname)s [%(name)s] %(filename)s:%(lineno)d %(message)s",
}

_TRUE_VALUES = {"1", "true", "yes", "on", "y", "enabled", "enable"}
_FALSE_VALUES = {"0", "false", "no", "off", "n", "disabled", "disable"}

_LEVEL_NAMES: dict[str, int] = {
    "TRACE": TRACE_LEVEL,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "FATAL": logging.CRITICAL,
}


class ConsoleHandlerConfigError(ValueError):
    """Raised when console handler settings cannot be interpreted."""


@dataclass(frozen=True)
class ConsoleHandlerConfig:
    """Normalized settings used to build a console ``StreamHandler``."""

    enabled: bool = True
    level: int = logging.INFO
    format_name: str = DEFAULT_CONSOLE_FORMAT
    format_text: str = _FORMATS[DEFAULT_CONSOLE_FORMAT]
    dev_only: bool = False
    stream: str = "stderr"
    datefmt: str | None = None
    handler_name: str | None = "console"

    def with_runtime_environment(self, *, is_development: bool | None = None) -> "ConsoleHandlerConfig":
        """Disable output at runtime when ``dev_only`` is true outside development."""

        if self.dev_only and not resolve_development_mode(is_development):
            return replace(self, enabled=False)
        return self


def create_console_handler(
    settings: Mapping[str, Any] | ConsoleHandlerConfig | Any | None = None,
    *,
    stream: TextIO | None = None,
    is_development: bool | None = None,
) -> logging.StreamHandler | None:
    """Create a configured ``logging.StreamHandler`` or return ``None``.

    ``settings`` may be a dict, a ``ConsoleHandlerConfig``, or any object with
    matching attributes. Supported dict keys include ``console_enabled``,
    ``console_level``, ``console_format``, ``console_stream``, ``datefmt``, and
    ``console_dev_only``.
    """

    config = build_console_handler_config(settings, is_development=is_development)
    if not config.enabled:
        return None

    register_trace_level()
    handler_stream = stream if stream is not None else stream_from_name(config.stream)
    handler = logging.StreamHandler(handler_stream)
    handler.setLevel(config.level)
    handler.setFormatter(logging.Formatter(config.format_text, datefmt=config.datefmt))
    if config.handler_name:
        handler.set_name(config.handler_name)
    return handler


def attach_console_handler(
    logger: logging.Logger,
    settings: Mapping[str, Any] | ConsoleHandlerConfig | Any | None = None,
    *,
    replace_existing: bool = False,
    stream: TextIO | None = None,
    is_development: bool | None = None,
) -> logging.StreamHandler | None:
    """Build a console handler, attach it to ``logger``, and return it.

    When console output is disabled, no handler is attached and ``None`` is
    returned. ``replace_existing`` removes stdout/stderr stream handlers first
    so repeated setup calls do not duplicate console output.
    """

    if replace_existing:
        remove_console_handlers(logger)

    handler = create_console_handler(settings, stream=stream, is_development=is_development)
    if handler is not None:
        logger.addHandler(handler)
    return handler


def build_console_handler_config(
    settings: Mapping[str, Any] | ConsoleHandlerConfig | Any | None = None,
    *,
    default_enabled: bool = True,
    default_level: str | int = DEFAULT_CONSOLE_LEVEL,
    default_format: str = DEFAULT_CONSOLE_FORMAT,
    is_development: bool | None = None,
) -> ConsoleHandlerConfig:
    """Normalize loose console settings into ``ConsoleHandlerConfig``."""

    if isinstance(settings, ConsoleHandlerConfig):
        return settings.with_runtime_environment(is_development=is_development)

    source = settings_to_mapping(settings)
    enabled = parse_bool(first_present(source, "console_enabled", "consoleEnabled", "enable_console", "console", default=default_enabled), field_name="console_enabled")
    dev_only = parse_bool(first_present(source, "console_dev_only", "consoleDevOnly", "dev_only", default=False), field_name="console_dev_only")
    level = normalize_logging_level(first_present(source, "console_level", "consoleLevel", "level", default=default_level))
    format_name, format_text = select_console_format(first_present(source, "console_format", "consoleFormat", "format", default=default_format), default=default_format)
    stream = normalize_stream_name(first_present(source, "console_stream", "consoleStream", "stream", default="stderr"))
    datefmt = first_present(source, "console_datefmt", "consoleDatefmt", "datefmt", default=None)
    handler_name = first_present(source, "console_handler_name", "consoleHandlerName", "handler_name", default="console")

    config = ConsoleHandlerConfig(
        enabled=enabled,
        level=level,
        format_name=format_name,
        format_text=format_text,
        dev_only=dev_only,
        stream=stream,
        datefmt=None if datefmt is None else str(datefmt),
        handler_name=None if handler_name in {None, ""} else str(handler_name),
    )
    return config.with_runtime_environment(is_development=is_development)


def remove_console_handlers(logger: logging.Logger) -> list[logging.Handler]:
    """Remove stdout/stderr ``StreamHandler`` instances from ``logger``."""

    removed: list[logging.Handler] = []
    for handler in list(logger.handlers):
        if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) in {sys.stdout, sys.stderr}:
            logger.removeHandler(handler)
            removed.append(handler)
    return removed


def select_console_format(format_value: str | Mapping[str, Any] | None = None, *, default: str = DEFAULT_CONSOLE_FORMAT) -> tuple[str, str]:
    """Return ``(format_name, format_text)`` for preset or custom formats."""

    if isinstance(format_value, Mapping):
        explicit_text = format_value.get("format") or format_value.get("text")
        if explicit_text:
            return "custom", ensure_format_text(str(explicit_text))
        format_value = format_value.get("name") or format_value.get("format_name")

    clean = str(default if format_value is None or str(format_value).strip() == "" else format_value).strip()
    key = clean.lower().replace("-", "_")
    if key in _FORMATS:
        return key, _FORMATS[key]
    if "%(" in clean:
        return "custom", ensure_format_text(clean)
    allowed = ", ".join(sorted(_FORMATS))
    raise ConsoleHandlerConfigError(f"Unknown console format {clean!r}. Use one of: {allowed}, or pass a logging format string.")


def normalize_logging_level(value: str | int) -> int:
    """Convert a common level name or integer into a logging level value."""

    if isinstance(value, bool):
        raise ConsoleHandlerConfigError("Logging level must be a name or integer, not a boolean.")
    if isinstance(value, int):
        if value < 0:
            raise ConsoleHandlerConfigError(f"Logging level must be zero or greater, got {value}.")
        return value

    clean = str(value).strip()
    if clean == "":
        raise ConsoleHandlerConfigError("Logging level cannot be empty.")
    if clean.lstrip("+-").isdigit():
        return normalize_logging_level(int(clean))

    key = clean.upper().replace("-", "_")
    if key in _LEVEL_NAMES:
        return _LEVEL_NAMES[key]
    standard = logging.getLevelName(key)
    if isinstance(standard, int):
        return standard
    allowed = ", ".join(sorted(_LEVEL_NAMES))
    raise ConsoleHandlerConfigError(f"Unknown logging level {clean!r}. Use one of: {allowed}, or an integer level.")


def register_trace_level() -> None:
    """Register TRACE with standard logging if it is not registered yet."""

    if logging.getLevelName(TRACE_LEVEL) != "TRACE":
        logging.addLevelName(TRACE_LEVEL, "TRACE")


def parse_bool(value: Any, *, field_name: str) -> bool:
    """Parse flexible config booleans with clear errors."""

    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    clean = str(value).strip().lower()
    if clean in _TRUE_VALUES:
        return True
    if clean in _FALSE_VALUES:
        return False
    raise ConsoleHandlerConfigError(f"{field_name} must be a boolean-like value, got {value!r}.")


def normalize_stream_name(value: Any) -> str:
    """Return ``stderr`` or ``stdout`` from config input."""

    clean = str(value or "stderr").strip().lower()
    if clean in {"err", "stderr", "sys.stderr"}:
        return "stderr"
    if clean in {"out", "stdout", "sys.stdout"}:
        return "stdout"
    raise ConsoleHandlerConfigError(f"console_stream must be 'stderr' or 'stdout', got {value!r}.")


def stream_from_name(name: str) -> TextIO:
    """Resolve a normalized stream name to the current Python console stream."""

    normalized = normalize_stream_name(name)
    return sys.stdout if normalized == "stdout" else sys.stderr


def ensure_format_text(format_text: str) -> str:
    """Validate that a logging format string is usable by ``logging``."""

    clean = format_text.strip()
    if not clean:
        raise ConsoleHandlerConfigError("Console format text cannot be empty.")
    try:
        record = logging.LogRecord("check", logging.INFO, __file__, 1, "message", (), None)
        logging.Formatter(clean).format(record)
    except Exception as exc:
        raise ConsoleHandlerConfigError(f"Invalid console logging format {format_text!r}: {exc}") from exc
    return clean


def first_present(source: Mapping[str, Any], *keys: str, default: Any) -> Any:
    """Return the first present key even when the value is falsy."""

    for key in keys:
        if key in source:
            return source[key]
    return default


def settings_to_mapping(settings: Any | None) -> Mapping[str, Any]:
    """Read dict-like or dataclass/object-like settings as a mapping."""

    if settings is None:
        return {}
    if isinstance(settings, Mapping):
        return settings
    keys = (
        "enabled", "level", "format_name", "format_text", "dev_only", "stream", "datefmt", "handler_name",
        "console_enabled", "console_level", "console_format", "console_stream", "console_datefmt", "console_dev_only", "console_handler_name",
    )
    values = {key: getattr(settings, key) for key in keys if hasattr(settings, key)}
    if "format_text" in values and "console_format" not in values:
        values["console_format"] = {"format": values["format_text"]}
    if "enabled" in values and "console_enabled" not in values:
        values["console_enabled"] = values["enabled"]
    if "dev_only" in values and "console_dev_only" not in values:
        values["console_dev_only"] = values["dev_only"]
    return values


def resolve_development_mode(is_development: bool | None = None) -> bool:
    """Return whether development mode is active."""

    if is_development is not None:
        return bool(is_development)
    env_value = os.getenv("APP_ENV") or os.getenv("ENV") or os.getenv("PYTHON_ENV") or ""
    return env_value.strip().lower() in {"dev", "develop", "development", "local", "test", "testing"}
