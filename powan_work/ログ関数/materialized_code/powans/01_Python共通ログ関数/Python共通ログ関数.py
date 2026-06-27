# powan_id: node-704b909f82
# title: Python共通ログ関数
# parent:
# powanKind:
# codeLanguage: python

"""Common Python logging entry point.

This root powan ties the child logging powans into one small reusable module:
level normalization, logger acquisition, readable formatting, console output,
file output, exception recording, and per-application settings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import logging
from logging import Handler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from pathlib import Path
import re
import sys
import traceback
from typing import Any, TextIO

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback.
    tomllib = None  # type: ignore[assignment]

TRACE_LEVEL = 5
TRACE_NAME = "TRACE"
DEFAULT_LEVEL = "INFO"
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_TRUE_VALUES = {"1", "true", "yes", "on", "y", "enable", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "n", "disable", "disabled"}
_SAFE_FILE_STEM = re.compile(r"[^A-Za-z0-9._-]+")
_LEVEL_ALIASES = {
    "TRACE": "TRACE",
    "TRC": "TRACE",
    "VERBOSE": "TRACE",
    "DEBUG": "DEBUG",
    "DBG": "DEBUG",
    "INFO": "INFO",
    "INFORMATION": "INFO",
    "NOTICE": "INFO",
    "WARN": "WARNING",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "ERR": "ERROR",
    "EXCEPTION": "ERROR",
    "CRITICAL": "CRITICAL",
    "FATAL": "CRITICAL",
}
_LEVEL_VALUES = {
    "TRACE": TRACE_LEVEL,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
_SENSITIVE_KEY_PARTS = ("password", "passwd", "token", "secret", "api_key", "apikey", "authorization")


class LoggingSettingsError(ValueError):
    """Raised when logging settings cannot be interpreted safely."""


@dataclass(frozen=True)
class LoggingProfile:
    """Resolved app-specific logging settings."""

    app_name: str
    level_name: str = DEFAULT_LEVEL
    level_value: int = logging.INFO
    console_enabled: bool = True
    file_enabled: bool = False
    log_dir: Path = Path("logs")
    filename: str | None = None
    format_text: str = DEFAULT_FORMAT
    date_format: str = DEFAULT_DATE_FORMAT
    propagate: bool = False
    rotation: str = "none"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 7
    encoding: str = "utf-8"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def log_path(self) -> Path:
        return self.log_dir / (self.filename or f"{safe_app_name(self.app_name)}.log")

    def as_dict(self) -> dict[str, Any]:
        data = {
            "app_name": self.app_name,
            "level": self.level_name,
            "level_value": self.level_value,
            "console_enabled": self.console_enabled,
            "file_enabled": self.file_enabled,
            "log_dir": str(self.log_dir),
            "log_path": str(self.log_path),
            "format": self.format_text,
            "date_format": self.date_format,
            "propagate": self.propagate,
            "rotation": self.rotation,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "encoding": self.encoding,
        }
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class LoggingSetupResult:
    """Logger, profile, and handlers created by configure_logging."""

    logger: logging.Logger
    profile: LoggingProfile
    handlers: tuple[Handler, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "logger": self.logger.name,
            "profile": self.profile.as_dict(),
            "handlers": [type(handler).__name__ for handler in self.handlers],
        }


def configure_logging(
    app_name: str,
    *,
    default: Mapping[str, Any] | None = None,
    app: Mapping[str, Any] | str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
    env_prefix: str = "LOG_",
    logger: logging.Logger | None = None,
    replace_handlers: bool = True,
    console_stream: TextIO | None = None,
) -> LoggingSetupResult:
    """Configure and return a standard logger for one application."""

    config = load_logging_config(default=default, app=app, environ=environ, env_prefix=env_prefix)
    profile = build_logging_profile(app_name, config)
    selected_logger = logger or logging.getLogger(profile.app_name)

    register_trace_level()
    selected_logger.setLevel(profile.level_value)
    selected_logger.propagate = profile.propagate
    if replace_handlers:
        selected_logger.handlers.clear()

    handlers: list[Handler] = []
    for handler in (
        create_console_handler(profile, stream=console_stream),
        create_file_handler(profile),
    ):
        if handler is not None:
            selected_logger.addHandler(handler)
            handlers.append(handler)

    return LoggingSetupResult(selected_logger, profile, tuple(handlers))


def get_logger(app_name: str, **settings: Any) -> logging.Logger:
    """Convenience entry point: get a configured logger with one call."""

    return configure_logging(app_name, app=settings or None).logger


def load_logging_config(
    *,
    default: Mapping[str, Any] | None = None,
    app: Mapping[str, Any] | str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
    env_prefix: str = "LOG_",
) -> dict[str, Any]:
    """Merge default settings, app settings, and environment overrides."""

    if app is None:
        app_config: dict[str, Any] = {}
    elif isinstance(app, (str, os.PathLike)):
        app_config = load_config_file(app)
    else:
        app_config = dict(app)
    return merge_config(default or {}, app_config, env_override_config(environ=environ, prefix=env_prefix))


def load_config_file(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a UTF-8 JSON or TOML logging config file."""

    config_path = Path(path)
    if config_path.suffix.lower() == ".json":
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    elif config_path.suffix.lower() == ".toml":
        if tomllib is None:
            raise LoggingSettingsError("TOML config requires Python 3.11+ tomllib.")
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
    else:
        raise LoggingSettingsError(f"Unsupported logging config file type: {config_path.suffix or '<none>'}.")
    if not isinstance(loaded, Mapping):
        raise LoggingSettingsError("Logging config file must contain a top-level mapping.")
    return dict(loaded)


def env_override_config(*, environ: Mapping[str, str] | None = None, prefix: str = "LOG_") -> dict[str, Any]:
    """Translate LOG_* environment variables into settings."""

    source = os.environ if environ is None else environ
    mapping = {
        "LEVEL": ("level", str.strip),
        "CONSOLE": ("console", parse_env_value),
        "FILE": ("file", parse_env_value),
        "DIR": ("log_dir", str.strip),
        "PATH": ("log_dir", str.strip),
        "FILENAME": ("filename", str.strip),
        "FORMAT": ("format", str),
        "ROTATION": ("rotation", str.strip),
        "MAX_BYTES": ("max_bytes", parse_int),
        "BACKUP_COUNT": ("backup_count", parse_int),
    }
    overrides: dict[str, Any] = {}
    for suffix, (target, caster) in mapping.items():
        raw = source.get(f"{prefix}{suffix}")
        if raw not in (None, ""):
            overrides[target] = caster(raw)
    return overrides


def build_logging_profile(app_name: str, config: Mapping[str, Any] | None = None) -> LoggingProfile:
    """Resolve loose settings into a strongly shaped logging profile."""

    source = config or {}
    clean_app_name = require_app_name(app_name)
    level_name, level_value = resolve_level(source.get("level", DEFAULT_LEVEL))
    rotation = str(source.get("rotation", "none") or "none").strip().lower()
    if rotation not in {"none", "size", "time"}:
        raise LoggingSettingsError("rotation must be 'none', 'size', or 'time'.")

    max_bytes = parse_int(source.get("max_bytes", 10 * 1024 * 1024))
    backup_count = parse_int(source.get("backup_count", 7))
    if rotation == "size" and max_bytes <= 0:
        raise LoggingSettingsError("size rotation requires max_bytes greater than 0.")
    if backup_count < 0:
        raise LoggingSettingsError("backup_count must be 0 or greater.")

    known = {
        "level", "console", "console_enabled", "file", "file_enabled", "propagate",
        "log_dir", "directory", "path", "filename", "file_name", "format", "date_format",
        "rotation", "max_bytes", "backup_count", "encoding",
    }
    return LoggingProfile(
        app_name=clean_app_name,
        level_name=level_name,
        level_value=level_value,
        console_enabled=parse_bool(first_present(source, "console", "console_enabled", default=True), field="console"),
        file_enabled=parse_bool(first_present(source, "file", "file_enabled", default=False), field="file"),
        log_dir=Path(str(first_present(source, "log_dir", "directory", "path", default="logs"))).expanduser(),
        filename=normalize_filename(source.get("filename") or source.get("file_name")),
        format_text=str(source.get("format", DEFAULT_FORMAT) or DEFAULT_FORMAT),
        date_format=str(source.get("date_format", DEFAULT_DATE_FORMAT) or DEFAULT_DATE_FORMAT),
        propagate=parse_bool(source.get("propagate", False), field="propagate"),
        rotation=rotation,
        max_bytes=max_bytes,
        backup_count=backup_count,
        encoding=str(source.get("encoding", "utf-8") or "utf-8"),
        extra={key: value for key, value in source.items() if key not in known},
    )


def create_console_handler(profile: LoggingProfile, *, stream: TextIO | None = None) -> Handler | None:
    """Create a console handler for a resolved profile."""

    if not profile.console_enabled:
        return None
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    prepare_handler(handler, profile)
    return handler


def create_file_handler(profile: LoggingProfile) -> Handler | None:
    """Create a file handler, including optional rotation."""

    if not profile.file_enabled:
        return None
    profile.log_dir.mkdir(parents=True, exist_ok=True)
    if profile.rotation == "size":
        handler: Handler = RotatingFileHandler(
            profile.log_path,
            maxBytes=profile.max_bytes,
            backupCount=profile.backup_count,
            encoding=profile.encoding,
        )
    elif profile.rotation == "time":
        handler = TimedRotatingFileHandler(
            profile.log_path,
            when="midnight",
            backupCount=profile.backup_count,
            encoding=profile.encoding,
        )
    else:
        handler = logging.FileHandler(profile.log_path, encoding=profile.encoding)
    prepare_handler(handler, profile)
    return handler


def prepare_handler(handler: Handler, profile: LoggingProfile) -> Handler:
    handler.setLevel(profile.level_value)
    handler.setFormatter(logging.Formatter(profile.format_text, datefmt=profile.date_format))
    return handler


def log_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException | None = None,
    *,
    level: str = "error",
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Record an exception with readable traceback and optional safe context."""

    active_exc = exc or sys.exc_info()[1]
    if not isinstance(active_exc, BaseException):
        raise ValueError("exc is required when no active exception is being handled")
    safe_context = mask_context(context or {})
    trace = "".join(traceback.format_exception(type(active_exc), active_exc, active_exc.__traceback__)).rstrip()
    payload = {
        "type": type(active_exc).__name__,
        "qualified_type": f"{type(active_exc).__module__}.{type(active_exc).__qualname__}",
        "message": str(active_exc),
        "context": safe_context,
        "traceback": trace,
    }
    text = build_exception_message(message, payload)
    exc_info = (type(active_exc), active_exc, active_exc.__traceback__)
    if str(level).lower() in {"critical", "fatal"}:
        logger.critical(text, exc_info=exc_info, extra={"exception_record": payload})
    else:
        logger.error(text, exc_info=exc_info, extra={"exception_record": payload})
    return payload


def build_exception_message(message: str, payload: Mapping[str, Any]) -> str:
    parts = [message.rstrip(), f"Exception: {payload['qualified_type']}: {payload['message']}"]
    context = payload.get("context") or {}
    if context:
        parts.append("Context: " + ", ".join(f"{key}={value!r}" for key, value in sorted(context.items())))
    if payload.get("traceback"):
        parts.append("Traceback:\n" + str(payload["traceback"]).rstrip())
    return "\n".join(part for part in parts if part)


def register_trace_level() -> int:
    """Register TRACE with standard logging and add Logger.trace once."""

    logging.addLevelName(TRACE_LEVEL, TRACE_NAME)
    if not hasattr(logging.Logger, "trace"):
        def trace(self: logging.Logger, message: object, *args: object, **kwargs: object) -> None:
            if self.isEnabledFor(TRACE_LEVEL):
                self._log(TRACE_LEVEL, message, args, **kwargs)
        setattr(logging.Logger, "trace", trace)
    return TRACE_LEVEL


def resolve_level(value: Any) -> tuple[str, int]:
    """Normalize a log level and return (name, logging_value)."""

    if isinstance(value, bool):
        raise LoggingSettingsError("boolean values are not valid log levels")
    if isinstance(value, int):
        for name, level_value in _LEVEL_VALUES.items():
            if level_value == value:
                return name, value
        raise LoggingSettingsError(f"Unknown numeric log level: {value!r}.")
    token = str(value or DEFAULT_LEVEL).strip().upper().replace("-", "_").replace(" ", "_")
    try:
        name = _LEVEL_ALIASES[token]
    except KeyError as exc:
        raise LoggingSettingsError(f"Unknown log level: {value!r}.") from exc
    return name, _LEVEL_VALUES[name]


def merge_config(*configs: Mapping[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for config in configs:
        if config:
            merged.update(config)
    return merged


def parse_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    token = str(value).strip().lower()
    if token in _TRUE_VALUES:
        return True
    if token in _FALSE_VALUES:
        return False
    raise LoggingSettingsError(f"{field} must be a boolean-like value.")


def parse_env_value(value: str) -> bool | str:
    token = value.strip().lower()
    if token in _TRUE_VALUES:
        return True
    if token in _FALSE_VALUES:
        return False
    return value.strip()


def parse_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise LoggingSettingsError(f"Expected integer value, got {value!r}.") from exc


def first_present(source: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in source:
            return source[key]
    return default


def require_app_name(app_name: str) -> str:
    if not isinstance(app_name, str):
        raise LoggingSettingsError("app_name must be a string.")
    clean = app_name.strip()
    if not clean:
        raise LoggingSettingsError("app_name must not be empty.")
    return clean


def safe_app_name(app_name: str) -> str:
    return _SAFE_FILE_STEM.sub("_", app_name.strip()).strip("._-") or "app"


def normalize_filename(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    filename = Path(str(value).strip()).name
    if filename in {"", ".", ".."}:
        raise LoggingSettingsError("filename must be a safe file name.")
    return filename


def mask_context(context: Mapping[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in context.items():
        text_key = str(key)
        if any(part in text_key.lower().replace("-", "_") for part in _SENSITIVE_KEY_PARTS):
            masked[text_key] = "***"
        else:
            masked[text_key] = value
    return masked


__all__ = [
    "TRACE_LEVEL",
    "TRACE_NAME",
    "LoggingProfile",
    "LoggingSettingsError",
    "LoggingSetupResult",
    "build_logging_profile",
    "configure_logging",
    "create_console_handler",
    "create_file_handler",
    "get_logger",
    "load_logging_config",
    "log_exception",
    "register_trace_level",
    "resolve_level",
]
