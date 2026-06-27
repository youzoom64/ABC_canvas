# powan_id: node-b02107dcf5
# title: アプリ別プロファイル設定
# parent: node-a3e5f7eb89
# powanKind: nerve
# codeLanguage: python

"""Application-specific logging profile composition.

This nerve powan keeps the public entry point small: take shared defaults, apply
one application's override, validate the result, and expose values that connect
naturally to :mod:`logging`. Lower organ powans may replace the helper
functions here with more specialized implementations later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Callable, Mapping


ProfileMap = Mapping[str, Any]
ProfileValidator = Callable[[ProfileMap], ProfileMap]


class LoggingProfileError(ValueError):
    """Raised when an application logging profile cannot be built."""


@dataclass(frozen=True)
class AppLoggingProfile:
    """Resolved logging settings for one application."""

    app_name: str
    level: str = "INFO"
    log_dir: Path = Path("logs")
    console: bool = True
    file: bool = True
    filename: str | None = None
    propagate: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def logging_level(self) -> int:
        """Return the standard logging level value for this profile."""

        return level_name_to_logging_value(self.level)

    @property
    def log_path(self) -> Path:
        """Return the default file path used by file handlers."""

        name = self.filename or f"{safe_app_name(self.app_name)}.log"
        return self.log_dir / name

    def apply_to_logger(self, logger: logging.Logger) -> logging.Logger:
        """Apply profile-level logger settings without touching handlers."""

        logger.setLevel(self.logging_level)
        logger.propagate = self.propagate
        return logger

    def as_dict(self) -> dict[str, Any]:
        """Return a plain dictionary suitable for downstream handler builders."""

        data: dict[str, Any] = {
            "app_name": self.app_name,
            "level": self.level,
            "logging_level": self.logging_level,
            "log_dir": str(self.log_dir),
            "console": self.console,
            "file": self.file,
            "filename": self.filename,
            "log_path": str(self.log_path),
            "propagate": self.propagate,
        }
        data.update(self.extra)
        return data


def build_app_logging_profile(
    app_name: str,
    *,
    defaults: ProfileMap | None = None,
    profiles: Mapping[str, ProfileMap] | None = None,
    validator: ProfileValidator | None = None,
) -> AppLoggingProfile:
    """Build the resolved logging profile for ``app_name``."""

    normalized_app_name = require_app_name(app_name)
    merged = merge_app_profile_defaults(
        defaults or default_logging_profile_values(),
        select_app_override(normalized_app_name, profiles or {}),
    )
    merged["app_name"] = normalized_app_name

    validate = validator or validate_profile_values
    try:
        validated = dict(validate(merged))
    except LoggingProfileError:
        raise
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise LoggingProfileError(
            f"logging profile for {normalized_app_name!r} failed validation: {exc}"
        ) from exc

    return profile_from_mapping(validated)


def default_logging_profile_values() -> dict[str, Any]:
    """Return shared defaults used when no external default organ is wired."""

    return {
        "level": "INFO",
        "log_dir": "logs",
        "console": True,
        "file": True,
        "filename": None,
        "propagate": False,
    }


def merge_app_profile_defaults(defaults: ProfileMap, override: ProfileMap) -> dict[str, Any]:
    """Overlay one app override on top of shared defaults."""

    if not isinstance(defaults, Mapping):
        raise LoggingProfileError("logging profile defaults must be a mapping")
    if not isinstance(override, Mapping):
        raise LoggingProfileError("application logging profile override must be a mapping")

    merged = dict(defaults)
    merged.update({key: value for key, value in override.items() if value is not None})
    return merged


def select_app_override(app_name: str, profiles: Mapping[str, ProfileMap]) -> ProfileMap:
    """Return the override mapping for one app, or an empty mapping."""

    if not isinstance(profiles, Mapping):
        raise LoggingProfileError("application logging profiles must be a mapping")
    override = profiles.get(app_name, {})
    if override is None:
        return {}
    if not isinstance(override, Mapping):
        raise LoggingProfileError(
            f"logging profile override for {app_name!r} must be a mapping"
        )
    return override


def validate_profile_values(profile: ProfileMap) -> dict[str, Any]:
    """Validate a resolved profile with clear, user-facing errors."""

    missing = [key for key in ("app_name", "level", "log_dir") if key not in profile]
    if missing:
        raise LoggingProfileError(
            "logging profile is missing required value(s): " + ", ".join(missing)
        )

    app_name = require_app_name(str(profile["app_name"]))
    level = normalize_level_name(profile["level"])
    log_dir = Path(str(profile["log_dir"])).expanduser()
    console = require_bool(profile.get("console", True), "console")
    file_enabled = require_bool(profile.get("file", True), "file")
    propagate = require_bool(profile.get("propagate", False), "propagate")

    filename_value = profile.get("filename")
    filename = None if filename_value in (None, "") else str(filename_value)
    if filename is not None and any(part in filename for part in ("/", "\\")):
        raise LoggingProfileError(
            f"logging profile filename must be a file name, not a path: {filename!r}"
        )

    known_keys = {"app_name", "level", "log_dir", "console", "file", "filename", "propagate"}
    extra = {key: value for key, value in profile.items() if key not in known_keys}

    return {
        "app_name": app_name,
        "level": level,
        "log_dir": log_dir,
        "console": console,
        "file": file_enabled,
        "filename": filename,
        "propagate": propagate,
        **extra,
    }


def profile_from_mapping(profile: ProfileMap) -> AppLoggingProfile:
    """Create ``AppLoggingProfile`` from already validated values."""

    known_keys = {"app_name", "level", "log_dir", "console", "file", "filename", "propagate"}
    extra = {key: value for key, value in profile.items() if key not in known_keys}
    return AppLoggingProfile(
        app_name=str(profile["app_name"]),
        level=str(profile["level"]),
        log_dir=Path(profile["log_dir"]),
        console=bool(profile.get("console", True)),
        file=bool(profile.get("file", True)),
        filename=profile.get("filename"),
        propagate=bool(profile.get("propagate", False)),
        extra=extra,
    )


def normalize_level_name(value: Any) -> str:
    """Normalize a level name while accepting standard logging integers."""

    if isinstance(value, int):
        name = logging.getLevelName(value)
        if isinstance(name, str) and not name.startswith("Level "):
            return name.upper()
        raise LoggingProfileError(f"unknown logging level value: {value!r}")

    name = str(value).strip().upper()
    aliases = {"WARN": "WARNING", "FATAL": "CRITICAL"}
    name = aliases.get(name, name)
    if name not in logging._nameToLevel and name != "TRACE":
        raise LoggingProfileError(f"unknown logging level name: {value!r}")
    return name


def level_name_to_logging_value(level: str) -> int:
    """Convert a normalized level name to a logging integer."""

    normalized = normalize_level_name(level)
    if normalized == "TRACE":
        return 5
    return int(logging._nameToLevel[normalized])


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
    raise LoggingProfileError(f"logging profile field {field_name!r} must be a boolean")


def require_app_name(app_name: str) -> str:
    """Return a clean app name or raise a helpful error."""

    cleaned = str(app_name).strip()
    if not cleaned:
        raise LoggingProfileError("application name for logging profile must not be empty")
    return cleaned


def safe_app_name(app_name: str) -> str:
    """Return a conservative file-name fragment for an app name."""

    cleaned = []
    for char in app_name.strip():
        cleaned.append(char if char.isalnum() or char in {"-", "_", "."} else "_")
    return "".join(cleaned).strip("._") or "application"
