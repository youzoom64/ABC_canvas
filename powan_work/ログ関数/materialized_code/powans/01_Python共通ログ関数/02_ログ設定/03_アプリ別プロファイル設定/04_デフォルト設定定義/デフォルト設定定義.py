# powan_id: node-87a78030ef
# title: デフォルト設定定義
# parent: node-b02107dcf5
# powanKind: organ
# codeLanguage: python

"""Shared defaults, app override merging, validation, and logger setup specs."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from logging import Handler, Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, MutableSequence, Sequence


class LoggingDefaultsError(ValueError):
    pass


DEFAULT_LEVEL = "INFO"
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_CONSOLE = True
DEFAULT_FILE = True
DEFAULT_FILENAME: str | None = None
DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_PROPAGATE = False
DEFAULT_ENCODING = "utf-8"
DEFAULT_MAX_BYTES = 0
DEFAULT_BACKUP_COUNT = 0
DEFAULT_FILE_MODE = "a"

DEFAULT_KEYS = {
    "level",
    "log_dir",
    "console",
    "file",
    "filename",
    "format",
    "date_format",
    "propagate",
    "encoding",
    "max_bytes",
    "backup_count",
    "file_mode",
}
PROFILE_KEYS = DEFAULT_KEYS | {"app_name"}


@dataclass(frozen=True)
class LoggingDefaults:
    level: str = DEFAULT_LEVEL
    log_dir: Path = DEFAULT_LOG_DIR
    console: bool = DEFAULT_CONSOLE
    file: bool = DEFAULT_FILE
    filename: str | None = DEFAULT_FILENAME
    format: str = DEFAULT_FORMAT
    date_format: str = DEFAULT_DATE_FORMAT
    propagate: bool = DEFAULT_PROPAGATE
    encoding: str = DEFAULT_ENCODING
    max_bytes: int = DEFAULT_MAX_BYTES
    backup_count: int = DEFAULT_BACKUP_COUNT
    file_mode: str = DEFAULT_FILE_MODE

    @property
    def logging_level(self) -> int:
        return level_name_to_logging_value(self.level)

    def to_dict(self, *, stringify_paths: bool = False) -> dict[str, Any]:
        log_dir: str | Path = str(self.log_dir) if stringify_paths else self.log_dir
        return {
            "level": self.level,
            "logging_level": self.logging_level,
            "log_dir": log_dir,
            "console": self.console,
            "file": self.file,
            "filename": self.filename,
            "format": self.format,
            "date_format": self.date_format,
            "propagate": self.propagate,
            "encoding": self.encoding,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "file_mode": self.file_mode,
        }


@dataclass(frozen=True)
class AppLoggingProfile:
    app_name: str
    defaults: LoggingDefaults = field(default_factory=LoggingDefaults)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def level(self) -> str:
        return self.defaults.level

    @property
    def logging_level(self) -> int:
        return self.defaults.logging_level

    @property
    def log_path(self) -> Path:
        name = self.defaults.filename or f"{safe_app_name(self.app_name)}.log"
        return self.defaults.log_dir / name

    def to_dict(self, *, stringify_paths: bool = False) -> dict[str, Any]:
        data = self.defaults.to_dict(stringify_paths=stringify_paths)
        data.update(
            {
                "app_name": self.app_name,
                "log_path": str(self.log_path) if stringify_paths else self.log_path,
            }
        )
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class HandlerSpec:
    kind: str
    level: str
    formatter: str
    date_format: str
    path: Path | None = None
    encoding: str = DEFAULT_ENCODING
    mode: str = DEFAULT_FILE_MODE
    max_bytes: int = DEFAULT_MAX_BYTES
    backup_count: int = DEFAULT_BACKUP_COUNT

    def to_dict(self, *, stringify_paths: bool = False) -> dict[str, Any]:
        path: str | Path | None = self.path
        if stringify_paths and path is not None:
            path = str(path)
        return {
            "kind": self.kind,
            "level": self.level,
            "formatter": self.formatter,
            "date_format": self.date_format,
            "path": path,
            "encoding": self.encoding,
            "mode": self.mode,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
        }


@dataclass(frozen=True)
class LoggerSetupSpec:
    logger_name: str
    level: str
    logging_level: int
    propagate: bool
    handlers: tuple[HandlerSpec, ...]

    def to_dict(self, *, stringify_paths: bool = False) -> dict[str, Any]:
        return {
            "logger_name": self.logger_name,
            "level": self.level,
            "logging_level": self.logging_level,
            "propagate": self.propagate,
            "handlers": [h.to_dict(stringify_paths=stringify_paths) for h in self.handlers],
        }


def default_logging_profile_values(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return build_logging_defaults(overrides).to_dict()


def logging_defaults_as_strings(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return build_logging_defaults(overrides).to_dict(stringify_paths=True)


def build_logging_defaults(overrides: Mapping[str, Any] | None = None) -> LoggingDefaults:
    raw = {
        "level": DEFAULT_LEVEL,
        "log_dir": DEFAULT_LOG_DIR,
        "console": DEFAULT_CONSOLE,
        "file": DEFAULT_FILE,
        "filename": DEFAULT_FILENAME,
        "format": DEFAULT_FORMAT,
        "date_format": DEFAULT_DATE_FORMAT,
        "propagate": DEFAULT_PROPAGATE,
        "encoding": DEFAULT_ENCODING,
        "max_bytes": DEFAULT_MAX_BYTES,
        "backup_count": DEFAULT_BACKUP_COUNT,
        "file_mode": DEFAULT_FILE_MODE,
    }
    return defaults_from_mapping(merge_default_overrides(raw, overrides or {}))


def merge_default_overrides(
    defaults: Mapping[str, Any], overrides: Mapping[str, Any]
) -> dict[str, Any]:
    require_mapping(defaults, "logging defaults")
    require_mapping(overrides, "logging default overrides")
    reject_unknown(overrides, DEFAULT_KEYS, "logging default override")
    merged = dict(defaults)
    merged.update({key: value for key, value in overrides.items() if value is not None})
    return merged


def build_app_logging_profile(
    app_name: Any,
    *,
    defaults: Mapping[str, Any] | LoggingDefaults | None = None,
    profiles: Mapping[str, Mapping[str, Any] | None] | None = None,
    override: Mapping[str, Any] | None = None,
) -> AppLoggingProfile:
    name = require_app_name(app_name)
    base = defaults.to_dict() if isinstance(defaults, LoggingDefaults) else defaults
    shared = default_logging_profile_values(base)
    app_override = select_app_override(name, profiles or {})
    if override:
        app_override = merge_profile_overrides(app_override, override)
    merged = merge_profile_overrides(shared, app_override)
    merged["app_name"] = name
    return profile_from_mapping(validate_profile_values(merged))


def select_app_override(
    app_name: str, profiles: Mapping[str, Mapping[str, Any] | None]
) -> dict[str, Any]:
    require_mapping(profiles, "application logging profiles")
    override = profiles.get(app_name, {})
    if override is None:
        return {}
    require_mapping(override, f"logging profile override for {app_name!r}")
    return dict(override)


def merge_profile_overrides(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(base, "logging profile base")
    require_mapping(override, "logging profile override")
    reject_unknown(override, PROFILE_KEYS, "logging profile override")
    merged = dict(base)
    merged.update({key: value for key, value in override.items() if value is not None})
    return merged


def validate_profile_values(values: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(values, "logging profile")
    if "app_name" not in values:
        raise LoggingDefaultsError("logging profile is missing required key: app_name")
    defaults = defaults_from_mapping(values)
    known = PROFILE_KEYS | {"logging_level", "log_path"}
    extra = {key: value for key, value in values.items() if key not in known}
    return {"app_name": require_app_name(values["app_name"]), **defaults.to_dict(), **extra}


def profile_from_mapping(values: Mapping[str, Any]) -> AppLoggingProfile:
    if "app_name" not in values:
        raise LoggingDefaultsError("logging profile is missing required key: app_name")
    defaults = defaults_from_mapping(values)
    known = PROFILE_KEYS | {"logging_level", "log_path"}
    extra = {key: value for key, value in values.items() if key not in known}
    return AppLoggingProfile(require_app_name(values["app_name"]), defaults, extra)


def defaults_from_mapping(values: Mapping[str, Any]) -> LoggingDefaults:
    missing = sorted(DEFAULT_KEYS - set(values))
    if missing:
        raise LoggingDefaultsError(
            "logging defaults are missing required key(s): " + ", ".join(missing)
        )
    return LoggingDefaults(
        level=normalize_level_name(values["level"]),
        log_dir=normalize_log_dir(values["log_dir"]),
        console=require_bool(values["console"], "console"),
        file=require_bool(values["file"], "file"),
        filename=normalize_filename(values["filename"]),
        format=require_non_empty_text(values["format"], "format"),
        date_format=require_non_empty_text(values["date_format"], "date_format"),
        propagate=require_bool(values["propagate"], "propagate"),
        encoding=require_non_empty_text(values["encoding"], "encoding"),
        max_bytes=require_non_negative_int(values["max_bytes"], "max_bytes"),
        backup_count=require_non_negative_int(values["backup_count"], "backup_count"),
        file_mode=normalize_file_mode(values["file_mode"]),
    )


def build_logger_setup_spec(
    profile: AppLoggingProfile | Mapping[str, Any], *, logger_name: str | None = None
) -> LoggerSetupSpec:
    resolved = profile if isinstance(profile, AppLoggingProfile) else profile_from_mapping(profile)
    handlers: list[HandlerSpec] = []
    if resolved.defaults.console:
        handlers.append(
            HandlerSpec("console", resolved.level, resolved.defaults.format, resolved.defaults.date_format)
        )
    if resolved.defaults.file:
        handlers.append(
            HandlerSpec(
                "file",
                resolved.level,
                resolved.defaults.format,
                resolved.defaults.date_format,
                resolved.log_path,
                resolved.defaults.encoding,
                resolved.defaults.file_mode,
                resolved.defaults.max_bytes,
                resolved.defaults.backup_count,
            )
        )
    return LoggerSetupSpec(
        logger_name or resolved.app_name,
        resolved.level,
        resolved.logging_level,
        resolved.defaults.propagate,
        tuple(handlers),
    )


def logger_setup_as_dict(
    profile: AppLoggingProfile | Mapping[str, Any],
    *,
    logger_name: str | None = None,
    stringify_paths: bool = True,
) -> dict[str, Any]:
    return build_logger_setup_spec(profile, logger_name=logger_name).to_dict(
        stringify_paths=stringify_paths
    )


def configure_logger(
    profile: AppLoggingProfile | Mapping[str, Any],
    *,
    logger: Logger | None = None,
    logger_name: str | None = None,
    replace_handlers: bool = True,
) -> Logger:
    setup = build_logger_setup_spec(profile, logger_name=logger_name)
    target = logger or logging.getLogger(setup.logger_name)
    target.setLevel(setup.logging_level)
    target.propagate = setup.propagate
    if replace_handlers:
        close_handlers(target.handlers)
        target.handlers.clear()
    for spec in setup.handlers:
        target.addHandler(create_handler(spec))
    return target


def create_handler(spec: HandlerSpec | Mapping[str, Any]) -> Handler:
    handler_spec = spec if isinstance(spec, HandlerSpec) else handler_spec_from_mapping(spec)
    formatter = logging.Formatter(handler_spec.formatter, handler_spec.date_format)
    if handler_spec.kind == "console":
        handler: Handler = logging.StreamHandler()
    elif handler_spec.kind == "file":
        if handler_spec.path is None:
            raise LoggingDefaultsError("file handler spec requires a path")
        handler_spec.path.parent.mkdir(parents=True, exist_ok=True)
        if handler_spec.max_bytes > 0:
            handler = RotatingFileHandler(
                handler_spec.path,
                maxBytes=handler_spec.max_bytes,
                backupCount=handler_spec.backup_count,
                encoding=handler_spec.encoding,
            )
        else:
            handler = logging.FileHandler(
                handler_spec.path, mode=handler_spec.mode, encoding=handler_spec.encoding
            )
    else:
        raise LoggingDefaultsError(f"unknown handler kind: {handler_spec.kind!r}")
    handler.setLevel(level_name_to_logging_value(handler_spec.level))
    handler.setFormatter(formatter)
    return handler


def handler_spec_from_mapping(values: Mapping[str, Any]) -> HandlerSpec:
    require_mapping(values, "handler spec")
    path_value = values.get("path")
    return HandlerSpec(
        kind=require_non_empty_text(values.get("kind"), "kind"),
        level=normalize_level_name(values.get("level", DEFAULT_LEVEL)),
        formatter=require_non_empty_text(values.get("formatter", DEFAULT_FORMAT), "formatter"),
        date_format=require_non_empty_text(values.get("date_format", DEFAULT_DATE_FORMAT), "date_format"),
        path=None if path_value in (None, "") else Path(str(path_value)).expanduser(),
        encoding=require_non_empty_text(values.get("encoding", DEFAULT_ENCODING), "encoding"),
        mode=normalize_file_mode(values.get("mode", DEFAULT_FILE_MODE)),
        max_bytes=require_non_negative_int(values.get("max_bytes", 0), "max_bytes"),
        backup_count=require_non_negative_int(values.get("backup_count", 0), "backup_count"),
    )


def close_handlers(handlers: MutableSequence[Handler] | Sequence[Handler]) -> None:
    for handler in list(handlers):
        handler.close()


def normalize_level_name(value: Any) -> str:
    if isinstance(value, bool):
        raise LoggingDefaultsError(f"logging level must be a name or integer, got {value!r}")
    if isinstance(value, int):
        name = logging.getLevelName(value)
        if isinstance(name, str) and not name.startswith("Level "):
            return name.upper()
        if value == 5:
            return "TRACE"
        raise LoggingDefaultsError(f"unknown logging level value: {value!r}")
    name = str(value).strip().upper()
    name = {"WARN": "WARNING", "FATAL": "CRITICAL"}.get(name, name)
    if name not in logging._nameToLevel and name != "TRACE":
        raise LoggingDefaultsError(f"unknown logging level name: {value!r}")
    return name


def level_name_to_logging_value(level: Any) -> int:
    normalized = normalize_level_name(level)
    return 5 if normalized == "TRACE" else int(logging._nameToLevel[normalized])


def normalize_log_dir(value: Any) -> Path:
    text = str(value).strip()
    if not text:
        raise LoggingDefaultsError("logging default log_dir must not be empty")
    return Path(text).expanduser()


def normalize_filename(value: Any) -> str | None:
    if value in (None, ""):
        return None
    filename = str(value).strip()
    if not filename:
        return None
    if filename in {".", ".."} or any(separator in filename for separator in ("/", chr(92))):
        raise LoggingDefaultsError(
            f"logging default filename must be a file name, not a path: {filename!r}"
        )
    return filename


def normalize_file_mode(value: Any) -> str:
    mode = str(value).strip()
    if mode not in {"a", "w", "x"}:
        raise LoggingDefaultsError("logging file_mode must be one of: a, w, x")
    return mode


def require_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise LoggingDefaultsError(f"logging default field {field_name!r} must be a boolean")


def require_non_empty_text(value: Any, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise LoggingDefaultsError(f"logging default field {field_name!r} must not be empty")
    return text


def require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise LoggingDefaultsError(f"logging default field {field_name!r} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise LoggingDefaultsError(f"logging default field {field_name!r} must be an integer") from exc
    if number < 0:
        raise LoggingDefaultsError(f"logging default field {field_name!r} must not be negative")
    return number


def require_app_name(app_name: Any) -> str:
    cleaned = str(app_name).strip()
    if not cleaned:
        raise LoggingDefaultsError("application name for logging profile must not be empty")
    return cleaned


def require_mapping(value: Any, name: str) -> None:
    if not isinstance(value, Mapping):
        raise LoggingDefaultsError(f"{name} must be a mapping")


def reject_unknown(values: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise LoggingDefaultsError(f"unknown {label} key(s): " + ", ".join(unknown))


def safe_app_name(app_name: str) -> str:
    blocked = {"/", chr(92), ":", "*", "?", '"', "<", ">", "|"}
    cleaned = [char if char not in blocked and not char.isspace() else "_" for char in app_name.strip()]
    return "".join(cleaned).strip("._") or "application"


__all__ = [
    "AppLoggingProfile", "HandlerSpec", "LoggerSetupSpec", "LoggingDefaults", "LoggingDefaultsError",
    "build_app_logging_profile", "build_logger_setup_spec", "build_logging_defaults", "configure_logger",
    "create_handler", "default_logging_profile_values", "handler_spec_from_mapping", "logger_setup_as_dict",
    "logging_defaults_as_strings", "merge_default_overrides", "merge_profile_overrides", "profile_from_mapping",
    "select_app_override", "validate_profile_values",
]
