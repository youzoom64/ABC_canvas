# powan_id: node-1ea0b0eb9e
# title: アプリ設定上書き
# parent: node-b02107dcf5
# powanKind: organ
# codeLanguage: python

"""Application logging profile overlay and settings generation.

This organ powan turns shared logging defaults plus one application's override
into a validated, standard-logging-friendly settings object. It stays at the
profile/settings boundary: it does not create handlers or emit records, but it
returns dataclasses and dictionaries that handler-building powans can consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any


ProfileMap = Mapping[str, Any]
_DEFAULT_LOG_DIR = "logs"
_DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_ROTATION_MAX_BYTES = 1_048_576
_DEFAULT_ROTATION_BACKUP_COUNT = 5


class AppProfileSettingsError(ValueError):
    """Raised when an application logging settings profile cannot be built."""


@dataclass(frozen=True)
class RotationSettings:
    """File rotation settings expressed in logging-handler terms."""

    enabled: bool = False
    max_bytes: int = _DEFAULT_ROTATION_MAX_BYTES
    backup_count: int = _DEFAULT_ROTATION_BACKUP_COUNT

    def as_dict(self) -> dict[str, Any]:
        """Return a plain mapping for a RotatingFileHandler builder."""

        return {
            "enabled": self.enabled,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
        }


@dataclass(frozen=True)
class AppLoggingSettings:
    """Resolved logging settings for one application."""

    app_name: str
    logger_name: str
    level: str
    logging_level: int
    log_dir: Path
    filename: str
    log_path: Path
    console: bool = True
    file: bool = True
    propagate: bool = False
    format: str = _DEFAULT_FORMAT
    datefmt: str = _DEFAULT_DATE_FORMAT
    rotation: RotationSettings = field(default_factory=RotationSettings)
    extra: dict[str, Any] = field(default_factory=dict)

    def logger_config(self) -> dict[str, Any]:
        """Return settings that apply directly to ``logging.Logger``."""

        return {
            "name": self.logger_name,
            "level": self.logging_level,
            "level_name": self.level,
            "propagate": self.propagate,
        }

    def formatter_config(self) -> dict[str, Any]:
        """Return arguments suitable for ``logging.Formatter``."""

        return {
            "fmt": self.format,
            "datefmt": self.datefmt,
        }

    def handler_plan(self) -> dict[str, dict[str, Any]]:
        """Return a serializable plan for console and file handlers."""

        plan: dict[str, dict[str, Any]] = {}
        if self.console:
            plan["console"] = {
                "enabled": True,
                "level": self.logging_level,
                "formatter": self.formatter_config(),
            }
        if self.file:
            plan["file"] = {
                "enabled": True,
                "level": self.logging_level,
                "path": str(self.log_path),
                "formatter": self.formatter_config(),
                "rotation": self.rotation.as_dict(),
            }
        return plan

    def as_dict(self) -> dict[str, Any]:
        """Return a plain dictionary for downstream powans."""

        data = {
            "app_name": self.app_name,
            "logger_name": self.logger_name,
            "level": self.level,
            "logging_level": self.logging_level,
            "log_dir": str(self.log_dir),
            "filename": self.filename,
            "log_path": str(self.log_path),
            "console": self.console,
            "file": self.file,
            "propagate": self.propagate,
            "format": self.format,
            "datefmt": self.datefmt,
            "rotation": self.rotation.as_dict(),
            "logger": self.logger_config(),
            "handlers": self.handler_plan(),
        }
        data.update(self.extra)
        return data


def build_app_logging_settings(
    app_name: Any,
    defaults: ProfileMap | None = None,
    profiles: Mapping[str, ProfileMap | None] | None = None,
) -> AppLoggingSettings:
    """Build validated logging settings for exactly one app."""

    merged = overlay_app_logging_settings(
        app_name,
        defaults or default_logging_profile_values(),
        profiles or {},
    )
    return profile_from_mapping(merged)


def default_logging_profile_values() -> dict[str, Any]:
    """Return shared defaults for application logging profiles."""

    return {
        "level": "INFO",
        "logger_name": None,
        "log_dir": _DEFAULT_LOG_DIR,
        "filename": "{app}.log",
        "console": True,
        "file": True,
        "propagate": False,
        "format": _DEFAULT_FORMAT,
        "datefmt": _DEFAULT_DATE_FORMAT,
        "rotation": {
            "enabled": False,
            "max_bytes": _DEFAULT_ROTATION_MAX_BYTES,
            "backup_count": _DEFAULT_ROTATION_BACKUP_COUNT,
        },
    }


def overlay_app_logging_settings(
    app_name: Any,
    defaults: ProfileMap,
    profiles: Mapping[str, ProfileMap | None] | None = None,
) -> dict[str, Any]:
    """Return defaults overlaid with only ``app_name``'s override."""

    normalized_app_name = require_app_name(app_name)
    override = select_app_override(normalized_app_name, profiles or {})
    merged = merge_app_profile_defaults(defaults, override)
    merged["app_name"] = normalized_app_name
    return merged


def select_app_override(
    app_name: Any,
    profiles: Mapping[str, ProfileMap | None],
) -> dict[str, Any]:
    """Return a copy of the selected application's override mapping."""

    normalized_app_name = require_app_name(app_name)
    profile_map = require_profiles_mapping(profiles)
    override = profile_map.get(normalized_app_name)
    if override is None:
        return {}
    return dict(require_profile_mapping(override, f"logging profile override for {normalized_app_name!r}"))


def merge_app_profile_defaults(defaults: ProfileMap, override: ProfileMap | None) -> dict[str, Any]:
    """Merge shared defaults with one app override.

    ``None`` in an override means inheritance. Nested ``rotation`` values are
    merged so an app can override one rotation field without erasing the rest.
    """

    merged = copy_profile_mapping(require_profile_mapping(defaults, "logging profile defaults"))
    if override is None:
        return merged

    overlay = require_profile_mapping(override, "application logging profile override")
    for key, value in overlay.items():
        if value is None:
            continue
        if key == "rotation":
            merged[key] = merge_rotation_profile(merged.get("rotation"), value)
        else:
            merged[str(key)] = copy_profile_value(value)
    return merged


def merge_rotation_profile(default_rotation: Any, override_rotation: Any) -> dict[str, Any]:
    """Merge nested rotation dictionaries with inheritance for ``None``."""

    base = copy_profile_mapping(rotation_profile_or_default(default_rotation))
    override = require_profile_mapping(override_rotation, "application logging rotation override")
    for key, value in override.items():
        if value is not None:
            base[str(key)] = copy_profile_value(value)
    return base


def profile_from_mapping(profile: ProfileMap) -> AppLoggingSettings:
    """Validate a resolved mapping and create ``AppLoggingSettings``."""

    values = validate_profile_values(profile)
    app_name = values["app_name"]
    logger_name = values["logger_name"] or app_name
    log_dir = values["log_dir"]
    filename = values["filename"] or f"{safe_app_name(app_name)}.log"
    log_path = log_dir / filename

    known = {
        "app_name",
        "logger_name",
        "level",
        "logging_level",
        "log_dir",
        "filename",
        "console",
        "file",
        "propagate",
        "format",
        "datefmt",
        "rotation",
    }
    extra = {key: value for key, value in values.items() if key not in known}

    return AppLoggingSettings(
        app_name=app_name,
        logger_name=logger_name,
        level=values["level"],
        logging_level=values["logging_level"],
        log_dir=log_dir,
        filename=filename,
        log_path=log_path,
        console=values["console"],
        file=values["file"],
        propagate=values["propagate"],
        format=values["format"],
        datefmt=values["datefmt"],
        rotation=values["rotation"],
        extra=extra,
    )


def validate_profile_values(profile: ProfileMap) -> dict[str, Any]:
    """Validate a merged app profile and normalize standard logging values."""

    source = require_profile_mapping(profile, "logging profile")
    app_name = require_app_name(source.get("app_name"))
    level = normalize_level_name(source.get("level", "INFO"))
    logger_name = normalize_optional_text(source.get("logger_name"), "logger_name")
    log_dir = normalize_log_dir(source.get("log_dir", _DEFAULT_LOG_DIR))
    filename = normalize_filename(source.get("filename", "{app}.log"), app_name)
    console = require_bool(source.get("console", True), "console")
    file_enabled = require_bool(source.get("file", True), "file")
    propagate = require_bool(source.get("propagate", False), "propagate")
    fmt = require_non_empty_text(source.get("format", _DEFAULT_FORMAT), "format")
    datefmt = require_non_empty_text(source.get("datefmt", _DEFAULT_DATE_FORMAT), "datefmt")
    rotation = normalize_rotation_settings(source.get("rotation"))

    values = dict(source)
    values.update(
        {
            "app_name": app_name,
            "logger_name": logger_name,
            "level": level,
            "logging_level": level_name_to_logging_value(level),
            "log_dir": log_dir,
            "filename": filename,
            "console": console,
            "file": file_enabled,
            "propagate": propagate,
            "format": fmt,
            "datefmt": datefmt,
            "rotation": rotation,
        }
    )
    return values


def normalize_rotation_settings(value: Any) -> RotationSettings:
    """Return validated rotation settings."""

    data = rotation_profile_or_default(value)
    enabled = require_bool(data.get("enabled", False), "rotation.enabled")
    max_bytes = require_non_negative_int(data.get("max_bytes", _DEFAULT_ROTATION_MAX_BYTES), "rotation.max_bytes")
    backup_count = require_non_negative_int(data.get("backup_count", _DEFAULT_ROTATION_BACKUP_COUNT), "rotation.backup_count")
    return RotationSettings(enabled=enabled, max_bytes=max_bytes, backup_count=backup_count)


def rotation_profile_or_default(value: Any) -> dict[str, Any]:
    """Return a rotation mapping, accepting missing rotation as defaults."""

    if value in (None, ""):
        return dict(default_logging_profile_values()["rotation"])
    return dict(require_profile_mapping(value, "logging rotation settings"))


def normalize_level_name(value: Any) -> str:
    """Normalize a standard logging level name or integer."""

    if isinstance(value, bool):
        raise AppProfileSettingsError(f"logging level must be a name or integer, got {value!r}")
    if isinstance(value, int):
        if value == 5:
            return "TRACE"
        name = logging.getLevelName(value)
        if isinstance(name, str) and not name.startswith("Level "):
            return name.upper()
        raise AppProfileSettingsError(f"unknown logging level value: {value!r}")

    name = str(value).strip().upper()
    aliases = {"WARN": "WARNING", "FATAL": "CRITICAL"}
    name = aliases.get(name, name)
    if name == "TRACE" or name in logging._nameToLevel:
        return name
    raise AppProfileSettingsError(f"unknown logging level name: {value!r}")


def level_name_to_logging_value(level: str) -> int:
    """Return the integer level understood by ``logging``."""

    normalized = normalize_level_name(level)
    if normalized == "TRACE":
        return 5
    return int(logging._nameToLevel[normalized])


def normalize_log_dir(value: Any) -> Path:
    """Return a non-empty expanded log directory path."""

    text = require_non_empty_text(value, "log_dir")
    return Path(text).expanduser()


def normalize_filename(value: Any, app_name: str) -> str | None:
    """Return an optional file name with ``{app}`` expanded."""

    if value in (None, ""):
        return None
    filename = str(value).strip().replace("{app}", safe_app_name(app_name))
    if not filename:
        return None
    blocked = {"/", "\\"}
    if filename in {".", ".."} or any(char in filename for char in blocked):
        raise AppProfileSettingsError(f"logging profile filename must be a file name, not a path: {filename!r}")
    return filename


def require_bool(value: Any, field_name: str) -> bool:
    """Parse a strict boolean-ish config value."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise AppProfileSettingsError(f"logging profile field {field_name!r} must be a boolean")


def require_non_negative_int(value: Any, field_name: str) -> int:
    """Return a non-negative integer config value."""

    if isinstance(value, bool):
        raise AppProfileSettingsError(f"logging profile field {field_name!r} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise AppProfileSettingsError(f"logging profile field {field_name!r} must be an integer") from exc
    if number < 0:
        raise AppProfileSettingsError(f"logging profile field {field_name!r} must not be negative")
    return number


def normalize_optional_text(value: Any, field_name: str) -> str | None:
    """Return stripped text or ``None`` for optional string fields."""

    if value in (None, ""):
        return None
    return require_non_empty_text(value, field_name)


def require_non_empty_text(value: Any, field_name: str) -> str:
    """Return non-empty stripped text for config fields."""

    text = str(value).strip()
    if not text:
        raise AppProfileSettingsError(f"logging profile field {field_name!r} must not be empty")
    return text


def require_profiles_mapping(profiles: Any) -> Mapping[str, ProfileMap | None]:
    """Ensure the app profile collection is mapping-shaped."""

    if not isinstance(profiles, Mapping):
        raise AppProfileSettingsError("application logging profiles must be a mapping")
    return profiles


def require_profile_mapping(value: Any, label: str) -> ProfileMap:
    """Ensure one profile dictionary is mapping-shaped."""

    if not isinstance(value, Mapping):
        raise AppProfileSettingsError(f"{label} must be a mapping")
    return value


def require_app_name(app_name: Any) -> str:
    """Return a non-empty app name for profile lookup and file names."""

    normalized = str(app_name).strip()
    if not normalized:
        raise AppProfileSettingsError("application name for logging profile must not be empty")
    return normalized


def copy_profile_mapping(values: ProfileMap) -> dict[str, Any]:
    """Copy a config-shaped mapping recursively."""

    return {str(key): copy_profile_value(value) for key, value in values.items()}


def copy_profile_value(value: Any) -> Any:
    """Copy nested config containers without deep-copying arbitrary objects."""

    if isinstance(value, Mapping):
        return copy_profile_mapping(value)
    if isinstance(value, list):
        return [copy_profile_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(copy_profile_value(item) for item in value)
    return value


def safe_app_name(app_name: str) -> str:
    """Return a conservative file-name fragment for an app name."""

    cleaned = []
    for char in require_app_name(app_name):
        cleaned.append(char if char.isalnum() or char in {"-", "_", "."} else "_")
    return "".join(cleaned).strip("._") or "application"


__all__ = [
    "AppLoggingSettings",
    "AppProfileSettingsError",
    "RotationSettings",
    "build_app_logging_settings",
    "default_logging_profile_values",
    "level_name_to_logging_value",
    "merge_app_profile_defaults",
    "overlay_app_logging_settings",
    "profile_from_mapping",
    "select_app_override",
    "validate_profile_values",
]
