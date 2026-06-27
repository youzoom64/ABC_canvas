# powan_id: node-ef620afdd3
# title: コンソール出力設定
# parent: node-a3e5f7eb89
# powanKind: organ
# codeLanguage: python

"""Console logging configuration helpers.

This module is an organ powan for deciding whether console logging is enabled,
which level should be shown, which format should be used, and how to build a
standard ``logging.StreamHandler`` from those settings.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, replace
from typing import Any, Mapping, TextIO


TRACE_LEVEL = 5
DEFAULT_CONSOLE_FORMAT = "standard"
DEFAULT_CONSOLE_LEVEL = "INFO"

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


class ConsoleOutputConfigError(ValueError):
    """Raised when console output settings cannot be interpreted."""


@dataclass(frozen=True)
class ConsoleOutputConfig:
    """Normalized console logging settings.

    Attributes:
        enabled: Whether a console handler should be created.
        level: Standard logging level value used by the handler.
        format_name: Name of the format selected from ``_FORMATS``.
        format_text: Formatter template passed to ``logging.Formatter``.
        dev_only: If true, console output is enabled only in development mode.
        stream: Console stream name. Either ``stderr`` or ``stdout``.
        datefmt: Optional date format for ``logging.Formatter``.
    """

    enabled: bool = True
    level: int = logging.INFO
    format_name: str = DEFAULT_CONSOLE_FORMAT
    format_text: str = _FORMATS[DEFAULT_CONSOLE_FORMAT]
    dev_only: bool = False
    stream: str = "stderr"
    datefmt: str | None = None

    def with_runtime_environment(self, *, is_development: bool | None = None) -> "ConsoleOutputConfig":
        """Apply runtime-only rules such as ``dev_only``.

        ``dev_only`` keeps the user's chosen settings intact while disabling the
        console handler outside development. This lets config loaders normalize
        once and apply environment rules near handler creation.
        """

        if self.dev_only and not resolve_development_mode(is_development):
            return replace(self, enabled=False)
        return self


def register_trace_level() -> None:
    """Register TRACE with standard logging if it has not been registered."""

    if logging.getLevelName(TRACE_LEVEL) != "TRACE":
        logging.addLevelName(TRACE_LEVEL, "TRACE")


def resolve_console_enabled(
    settings: Mapping[str, Any] | None = None,
    *,
    default: bool = True,
    is_development: bool | None = None,
) -> bool:
    """Return whether console output should be enabled.

    Accepted keys are ``console``, ``console_enabled``, ``consoleEnabled``, and
    ``enable_console``. Missing values use ``default``. If ``dev_only`` is true,
    output is disabled unless development mode is active.
    """

    source = settings or {}
    enabled_value = first_present(
        source,
        "console_enabled",
        "consoleEnabled",
        "enable_console",
        "console",
        default=default,
    )
    enabled = parse_bool(enabled_value, field_name="console_enabled")
    dev_only = parse_bool(first_present(source, "console_dev_only", "consoleDevOnly", "dev_only", default=False), field_name="console_dev_only")
    if dev_only and not resolve_development_mode(is_development):
        return False
    return enabled


def select_console_format(
    format_value: str | Mapping[str, Any] | None = None,
    *,
    default: str = DEFAULT_CONSOLE_FORMAT,
) -> tuple[str, str]:
    """Return ``(format_name, format_text)`` for console output.

    ``format_value`` may be a known format name, a raw logging format string, or
    a mapping with ``name``/``format`` keys. Raw strings are accepted when they
    contain a ``%(`` logging placeholder.
    """

    if isinstance(format_value, Mapping):
        explicit_text = format_value.get("format") or format_value.get("text")
        if explicit_text:
            return "custom", ensure_format_text(str(explicit_text))
        format_value = format_value.get("name") or format_value.get("format_name")

    if format_value is None or str(format_value).strip() == "":
        format_value = default

    clean = str(format_value).strip()
    key = clean.lower().replace("-", "_")
    if key in _FORMATS:
        return key, _FORMATS[key]
    if "%(" in clean:
        return "custom", ensure_format_text(clean)
    allowed = ", ".join(sorted(_FORMATS))
    raise ConsoleOutputConfigError(f"Unknown console format {clean!r}. Use one of: {allowed}, or pass a logging format string.")


def build_console_output_config(
    settings: Mapping[str, Any] | ConsoleOutputConfig | None = None,
    *,
    default_enabled: bool = True,
    default_level: str | int = DEFAULT_CONSOLE_LEVEL,
    default_format: str = DEFAULT_CONSOLE_FORMAT,
    is_development: bool | None = None,
) -> ConsoleOutputConfig:
    """Normalize loose console settings into ``ConsoleOutputConfig``."""

    if isinstance(settings, ConsoleOutputConfig):
        return settings.with_runtime_environment(is_development=is_development)

    source = settings or {}
    enabled = resolve_console_enabled(source, default=default_enabled, is_development=is_development)
    dev_only = parse_bool(first_present(source, "console_dev_only", "consoleDevOnly", "dev_only", default=False), field_name="console_dev_only")
    level = normalize_logging_level(first_present(source, "console_level", "consoleLevel", "level", default=default_level))
    format_name, format_text = select_console_format(
        first_present(source, "console_format", "consoleFormat", "format", default=default_format),
        default=default_format,
    )
    stream = normalize_stream_name(first_present(source, "console_stream", "consoleStream", "stream", default="stderr"))
    datefmt = first_present(source, "console_datefmt", "consoleDatefmt", "datefmt", default=None)
    if datefmt is not None:
        datefmt = str(datefmt)

    config = ConsoleOutputConfig(
        enabled=enabled,
        level=level,
        format_name=format_name,
        format_text=format_text,
        dev_only=dev_only,
        stream=stream,
        datefmt=datefmt,
    )
    return config.with_runtime_environment(is_development=is_development)


def create_console_handler(
    settings: Mapping[str, Any] | ConsoleOutputConfig | None = None,
    *,
    stream: TextIO | None = None,
    is_development: bool | None = None,
) -> logging.StreamHandler | None:
    """Create a configured ``logging.StreamHandler`` or return ``None``.

    Returning ``None`` for disabled output makes logger setup code easy to read:
    build all possible handlers, then attach the ones that are not ``None``.
    """

    config = build_console_output_config(settings, is_development=is_development)
    if not config.enabled:
        return None

    register_trace_level()
    handler_stream = stream if stream is not None else stream_from_name(config.stream)
    handler = logging.StreamHandler(handler_stream)
    handler.setLevel(config.level)
    handler.setFormatter(logging.Formatter(config.format_text, datefmt=config.datefmt))
    return handler


def attach_console_handler(
    logger: logging.Logger,
    settings: Mapping[str, Any] | ConsoleOutputConfig | None = None,
    *,
    replace_existing: bool = False,
    stream: TextIO | None = None,
    is_development: bool | None = None,
) -> logging.StreamHandler | None:
    """Attach a console handler to ``logger`` and return it.

    When ``replace_existing`` is true, existing ``StreamHandler`` instances that
    write to stdout or stderr are removed before the new handler is attached.
    """

    if replace_existing:
        remove_console_handlers(logger)
    handler = create_console_handler(settings, stream=stream, is_development=is_development)
    if handler is not None:
        logger.addHandler(handler)
    return handler


def remove_console_handlers(logger: logging.Logger) -> list[logging.Handler]:
    """Remove stdout/stderr stream handlers from a logger and return them."""

    removed: list[logging.Handler] = []
    for handler in list(logger.handlers):
        if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) in {sys.stdout, sys.stderr}:
            logger.removeHandler(handler)
            removed.append(handler)
    return removed


def normalize_logging_level(value: str | int) -> int:
    """Convert a common level name or integer into a logging level value."""

    if isinstance(value, bool):
        raise ConsoleOutputConfigError("Logging level must be a name or integer, not a boolean.")
    if isinstance(value, int):
        if value < 0:
            raise ConsoleOutputConfigError(f"Logging level must be zero or greater, got {value}.")
        return value

    clean = str(value).strip()
    if clean == "":
        raise ConsoleOutputConfigError("Logging level cannot be empty.")
    if clean.lstrip("+-").isdigit():
        return normalize_logging_level(int(clean))

    key = clean.upper().replace("-", "_")
    if key in _LEVEL_NAMES:
        return _LEVEL_NAMES[key]
    standard = logging.getLevelName(key)
    if isinstance(standard, int):
        return standard
    allowed = ", ".join(sorted(_LEVEL_NAMES))
    raise ConsoleOutputConfigError(f"Unknown logging level {clean!r}. Use one of: {allowed}, or an integer level.")


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
    raise ConsoleOutputConfigError(f"{field_name} must be a boolean-like value, got {value!r}.")


def first_present(source: Mapping[str, Any], *keys: str, default: Any) -> Any:
    """Return the first key present in ``source``, even if its value is falsy."""

    for key in keys:
        if key in source:
            return source[key]
    return default


def ensure_format_text(format_text: str) -> str:
    """Validate that a logging format string is plausible."""

    clean = format_text.strip()
    if not clean:
        raise ConsoleOutputConfigError("Console format text cannot be empty.")
    try:
        logging.Formatter(clean).format(logging.LogRecord("check", logging.INFO, __file__, 1, "message", (), None))
    except Exception as exc:  # logging raises several formatter-specific errors.
        raise ConsoleOutputConfigError(f"Invalid console logging format {format_text!r}: {exc}") from exc
    return clean


def normalize_stream_name(value: Any) -> str:
    """Return ``stderr`` or ``stdout`` from config input."""

    clean = str(value or "stderr").strip().lower()
    if clean in {"err", "stderr", "sys.stderr"}:
        return "stderr"
    if clean in {"out", "stdout", "sys.stdout"}:
        return "stdout"
    raise ConsoleOutputConfigError(f"console_stream must be 'stderr' or 'stdout', got {value!r}.")


def stream_from_name(name: str) -> TextIO:
    """Resolve a normalized stream name to a live Python stream."""

    normalized = normalize_stream_name(name)
    return sys.stdout if normalized == "stdout" else sys.stderr


def resolve_development_mode(is_development: bool | None = None) -> bool:
    """Return whether development-only console output should be active."""

    if is_development is not None:
        return bool(is_development)
    for key in ("APP_ENV", "PYTHON_ENV", "ENVIRONMENT", "ENV"):
        value = os.environ.get(key)
        if not value:
            continue
        clean = value.strip().lower()
        if clean in {"dev", "development", "local", "test", "testing"}:
            return True
        if clean in {"prod", "production", "stage", "staging"}:
            return False
    return False


def describe_console_output(config: Mapping[str, Any] | ConsoleOutputConfig | None = None) -> dict[str, Any]:
    """Return a serializable summary useful for diagnostics and tests."""

    normalized = build_console_output_config(config)
    return {
        "enabled": normalized.enabled,
        "level": normalized.level,
        "levelName": logging.getLevelName(normalized.level),
        "formatName": normalized.format_name,
        "format": normalized.format_text,
        "devOnly": normalized.dev_only,
        "stream": normalized.stream,
        "datefmt": normalized.datefmt,
    }


__all__ = [
    "ConsoleOutputConfig",
    "ConsoleOutputConfigError",
    "attach_console_handler",
    "build_console_output_config",
    "create_console_handler",
    "describe_console_output",
    "normalize_logging_level",
    "register_trace_level",
    "remove_console_handlers",
    "resolve_console_enabled",
    "select_console_format",
]
