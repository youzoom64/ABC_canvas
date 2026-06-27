# powan_id: node-a3e5f7eb89
# title: ログ設定
# parent: node-704b909f82
# powanKind:
# codeLanguage: python

"""Application logging setup entry point.

This powan resolves per-application logging settings and applies them to the
standard :mod:`logging` package.  It is intentionally self-contained: callers can
provide defaults, an app-specific mapping or JSON/TOML file, and LOG_* style
environment overrides, then receive one configured logger plus the resolved
profile that was used to build it.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from dataclasses import dataclass, field
import json
import logging
from logging import Handler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from pathlib import Path
import sys
from typing import Any, TextIO

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback.
    tomllib = None  # type: ignore[assignment]


TRACE_LEVEL = 5
TRACE_NAME = "TRACE"
DEFAULT_LEVEL = "INFO"
DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

_TRUE_VALUES = {"1", "true", "yes", "on", "y", "enable", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "n", "disable", "disabled"}
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


class LoggingSettingsError(ValueError):
    """Raised when logging settings cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
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
    propagate: bool = False
    rotation: str = "none"
    max_bytes: int = 0
    backup_count: int = 7
    encoding: str = "utf-8"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def log_path(self) -> Path:
        """Return the file path that will be used when file output is enabled."""

        return self.log_dir / (self.filename or f"{safe_app_name(self.app_name)}.log")

    def as_dict(self) -> dict[str, Any]:
        """Return a plain diagnostic dictionary for UIs and tests."""

        data: dict[str, Any] = {
            "app_name": self.app_name,
            "level": self.level_name,
            "level_value": self.level_value,
            "console_enabled": self.console_enabled,
            "file_enabled": self.file_enabled,
            "log_dir": str(self.log_dir),
            "log_path": str(self.log_path),
            "format": self.format_text,
            "propagate": self.propagate,
            "rotation": self.rotation,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "encoding": self.encoding,
        }
        data.update(self.extra)
        return data


@dataclass(frozen=True, slots=True)
class LoggingSetupResult:
    """Objects created by ``configure_logging``."""

    logger: logging.Logger
    profile: LoggingProfile
    handlers: tuple[Handler, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a compact summary of the configured logger."""

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
    """Configure and return a standard logger for one application.

    Merge order is ``default`` -> ``app`` -> environment overrides.  File output
    stays opt-in so small scripts do not create files unless the app requests it.
    """

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

    return LoggingSetupResult(logger=selected_logger, profile=profile, handlers=tuple(handlers))


def load_logging_config(
    *,
    default: Mapping[str, Any] | None = None,
    app: Mapping[str, Any] | str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
    env_prefix: str = "LOG_",
) -> dict[str, Any]:
    """Load defaults, app settings, and environment overrides into one dict."""

    if app is None:
        app_config: dict[str, Any] = {}
    elif isinstance(app, (str, os.PathLike)):
        app_config = load_config_file(app)
    else:
        app_config = plain_dict(app)

    return merge_config(default, app_config, env_override_config(environ=environ, prefix=env_prefix))


def load_config_file(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a UTF-8 JSON or TOML config file."""

    config_path = Path(path)
    suffix = config_path.suffix.lower()
    try:
        if suffix == ".json":
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
        elif suffix == ".toml":
            if tomllib is None:
                raise LoggingSettingsError("TOML config requires Python 3.11+ tomllib.")
            loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
        else:
            raise LoggingSettingsError(f"Unsupported logging config file type: {suffix or '<none>'}.")
    except OSError as exc:
        raise LoggingSettingsError(f"Failed to read logging config {config_path!s}: {exc}") from exc

    if not isinstance(loaded, Mapping):
        raise LoggingSettingsError("Logging config file must contain a top-level mapping.")
    return plain_dict(loaded)


def env_override_config(
    *,
    environ: Mapping[str, str] | None = None,
    prefix: str = "LOG_",
) -> dict[str, Any]:
    """Translate simple LOG_* variables into config overrides."""

    source = os.environ if environ is None else environ
    mapping = {
        "LEVEL": ("level", parse_env_value),
        "CONSOLE": ("console", parse_env_value),
        "FILE": ("file", parse_env_value),
        "PATH": ("log_dir", str.strip),
        "DIR": ("log_dir", str.strip),
        "FILENAME": ("filename", str.strip),
        "FORMAT": ("format", str),
        "ROTATION": ("rotation", str.strip),
        "MAX_BYTES": ("max_bytes", parse_int),
        "BACKUP_COUNT": ("backup_count", parse_int),
        "ENCODING": ("encoding", str.strip),
        "PROPAGATE": ("propagate", parse_env_value),
    }
    overrides: dict[str, Any] = {}
    for suffix, (target, caster) in mapping.items():
        raw = source.get(f"{prefix}{suffix}")
        if raw is None or raw == "":
            continue
        try:
            overrides[target] = caster(raw)
        except Exception as exc:  # noqa: BLE001 - keep the failing env key visible.
            raise LoggingSettingsError(f"Invalid environment override {prefix}{suffix}: {exc}") from exc
    return overrides


def build_logging_profile(app_name: str, config: Mapping[str, Any] | None = None) -> LoggingProfile:
    """Resolve loose config into a strongly shaped logging profile."""

    source = config or {}
    if not isinstance(source, Mapping):
        raise LoggingSettingsError("Logging config must be a mapping.")

    clean_app_name = require_app_name(app_name)
    level_name, level_value = resolve_level(source.get("level", DEFAULT_LEVEL))
    rotation = str(source.get("rotation", "none") or "none").strip().lower()
    if rotation not in {"none", "size", "time"}:
        raise LoggingSettingsError("rotation must be 'none', 'size', or 'time'.")

    max_bytes = parse_int(source.get("max_bytes", 0))
    backup_count = parse_int(source.get("backup_count", 7))
    if rotation == "size" and max_bytes <= 0:
        raise LoggingSettingsError("size rotation requires max_bytes greater than 0.")
    if backup_count < 0:
        raise LoggingSettingsError("backup_count must be 0 or greater.")

    known = {
        "level", "console", "console_enabled", "file", "file_enabled", "propagate",
        "log_dir", "directory", "path", "filename", "file_name", "format",
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
    handler.setLevel(profile.level_value)
    handler.setFormatter(logging.Formatter(profile.format_text))
    return handler


def create_file_handler(profile: LoggingProfile) -> Handler | None:
    """Create a file handler for a resolved profile."""

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
    handler.setLevel(profile.level_value)
    handler.setFormatter(logging.Formatter(profile.format_text))
    return handler


def register_trace_level() -> int:
    """Register TRACE with standard logging and add ``Logger.trace`` once."""

    logging.addLevelName(TRACE_LEVEL, TRACE_NAME)
    if not hasattr(logging.Logger, "trace"):

        def trace(self: logging.Logger, message: object, *args: object, **kwargs: object) -> None:
            if self.isEnabledFor(TRACE_LEVEL):
                self._log(TRACE_LEVEL, message, args, **kwargs)

        setattr(logging.Logger, "trace", trace)
    return TRACE_LEVEL


def resolve_level(value: Any) -> tuple[str, int]:
    """Normalize a log level and return ``(name, logging_value)``."""

    register_trace_level()
    if isinstance(value, bool):
        raise LoggingSettingsError("level must be a name or integer, not bool.")
    if isinstance(value, int):
        name = logging.getLevelName(value)
        if isinstance(name, str) and name in _LEVEL_VALUES:
            return name, value
        raise LoggingSettingsError(f"Unsupported numeric log level: {value!r}.")
    key = str(value if value is not None else DEFAULT_LEVEL).strip().replace("-", "_").replace(" ", "_").upper()
    if key in {"", "DEFAULT", "AUTO"}:
        key = DEFAULT_LEVEL
    canonical = _LEVEL_ALIASES.get(key)
    if canonical is None:
        raise LoggingSettingsError(f"Unknown log level {value!r}.")
    return canonical, _LEVEL_VALUES[canonical]


def parse_bool(value: Any, *, field: str) -> bool:
    """Parse a boolean-ish setting with a clear field name."""

    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    text = str(value).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    raise LoggingSettingsError(f"{field} must be a boolean-like value, got {value!r}.")


def parse_env_value(value: str) -> Any:
    """Parse environment strings into bool/int/float/None/string values."""

    text = value.strip()
    lowered = text.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    if lowered in {"none", "null"}:
        return None
    try:
        return int(text, 10)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def parse_int(value: Any) -> int:
    """Parse an integer logging setting."""

    if isinstance(value, bool):
        raise LoggingSettingsError("integer logging settings must not be bool.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise LoggingSettingsError(f"Expected integer logging setting, got {value!r}.") from exc


def first_present(source: Mapping[str, Any], *keys: str, default: Any) -> Any:
    """Return the first present key, preserving false-y configured values."""

    for key in keys:
        if key in source:
            return source[key]
    return default


def merge_config(*configs: Mapping[str, Any] | None) -> dict[str, Any]:
    """Deep-merge configs from left to right without mutating callers."""

    merged: dict[str, Any] = {}
    for config in configs:
        if config is not None:
            deep_merge(merged, plain_dict(config))
    return merged


def deep_merge(base: MutableMapping[str, Any], override: Mapping[str, Any]) -> None:
    """Merge nested mappings in place for ``merge_config``."""

    for key, value in override.items():
        current = base.get(key)
        if isinstance(current, MutableMapping) and isinstance(value, Mapping):
            deep_merge(current, value)
        else:
            base[str(key)] = deepcopy(value)


def plain_dict(source: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached plain dict with string keys."""

    if not isinstance(source, Mapping):
        raise LoggingSettingsError(f"Logging config must be a mapping, got {type(source).__name__}.")
    result: dict[str, Any] = {}
    for key, value in source.items():
        result[str(key)] = plain_dict(value) if isinstance(value, Mapping) else deepcopy(value)
    return result


def normalize_filename(value: Any) -> str | None:
    """Return a safe plain filename or None for the default app filename."""

    if value in (None, ""):
        return None
    filename = str(value).strip()
    candidate = Path(filename)
    if not filename or candidate.is_absolute() or candidate.parent != Path("."):
        raise LoggingSettingsError("filename must be a plain file name, not a path.")
    if filename in {".", ".."}:
        raise LoggingSettingsError("filename must name a log file.")
    return filename


def require_app_name(app_name: str) -> str:
    """Return a clean app name or raise a helpful error."""

    cleaned = str(app_name).strip()
    if not cleaned:
        raise LoggingSettingsError("app_name must not be empty.")
    return cleaned


def safe_app_name(app_name: str) -> str:
    """Return a conservative file-name fragment for an app name."""

    cleaned = [char if char.isalnum() or char in {"-", "_", "."} else "_" for char in app_name.strip()]
    return "".join(cleaned).strip("._") or "application"
