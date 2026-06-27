# powan_id: node-4c85113a81
# title: プロファイル検証
# parent: node-b02107dcf5
# powanKind: organ
# codeLanguage: python

"""Validation helpers for resolved application logging profiles.

This organ powan receives one already-resolved application logging profile,
checks that its values are usable, and returns a normalized plain dictionary.
It does not merge defaults or choose per-application overrides; the parent powan
owns that composition work.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping


ProfileMap = Mapping[str, Any]


class LoggingProfileValidationError(ValueError):
    """Raised when a resolved logging profile has an unusable value."""


def validate_profile_values(profile: ProfileMap) -> dict[str, Any]:
    """Validate and normalize one resolved logging profile.

    Required fields are ``app_name``, ``level``, and ``log_dir``. Optional
    fields are ``console``, ``file``, ``filename``, and ``propagate``. Unknown
    keys are preserved so neighboring powans can carry additional settings.
    """

    if not isinstance(profile, Mapping):
        raise LoggingProfileValidationError("logging profile must be a mapping")

    missing = [key for key in ("app_name", "level", "log_dir") if key not in profile]
    if missing:
        raise LoggingProfileValidationError(
            "logging profile is missing required value(s): " + ", ".join(missing)
        )

    app_name = require_non_empty_text(profile["app_name"], "app_name")
    level = normalize_level_name(profile["level"])
    log_dir = normalize_log_dir(profile["log_dir"])
    console = require_bool(profile.get("console", True), "console")
    file_enabled = require_bool(profile.get("file", True), "file")
    filename = normalize_filename(profile.get("filename"))
    propagate = require_bool(profile.get("propagate", False), "propagate")

    known_keys = {
        "app_name",
        "level",
        "log_dir",
        "console",
        "file",
        "filename",
        "propagate",
    }
    extra = {key: value for key, value in profile.items() if key not in known_keys}

    return {
        "app_name": app_name,
        "level": level,
        "logging_level": level_name_to_logging_value(level),
        "log_dir": log_dir,
        "console": console,
        "file": file_enabled,
        "filename": filename,
        "propagate": propagate,
        **extra,
    }


def normalize_level_name(value: Any) -> str:
    """Return a standard uppercase logging level name."""

    if isinstance(value, bool):
        raise LoggingProfileValidationError(
            f"logging level must be a name or integer, got {value!r}"
        )

    if isinstance(value, int):
        name = logging.getLevelName(value)
        if isinstance(name, str) and not name.startswith("Level "):
            return name.upper()
        if value == 5:
            return "TRACE"
        raise LoggingProfileValidationError(f"unknown logging level value: {value!r}")

    text = require_non_empty_text(value, "level").upper()
    aliases = {"WARN": "WARNING", "FATAL": "CRITICAL"}
    normalized = aliases.get(text, text)
    if normalized == "TRACE":
        return normalized
    if normalized not in logging._nameToLevel:
        raise LoggingProfileValidationError(f"unknown logging level name: {value!r}")
    return normalized


def level_name_to_logging_value(level: str) -> int:
    """Convert a normalized level name to the integer used by ``logging``."""

    normalized = normalize_level_name(level)
    if normalized == "TRACE":
        return 5
    return int(logging._nameToLevel[normalized])


def normalize_log_dir(value: Any) -> Path:
    """Return an expanded log directory path from config text or ``Path``."""

    if isinstance(value, Path):
        path = value
    else:
        path = Path(require_non_empty_text(value, "log_dir"))

    expanded = path.expanduser()
    if str(expanded).strip() == "":
        raise LoggingProfileValidationError("logging profile field 'log_dir' must not be empty")
    return expanded


def normalize_filename(value: Any) -> str | None:
    """Return a safe file name, or ``None`` when the default name should be used."""

    if value is None:
        return None
    filename = str(value).strip()
    if not filename:
        return None
    if filename in {".", ".."}:
        raise LoggingProfileValidationError(
            f"logging profile filename must be a file name: {filename!r}"
        )
    if any(separator in filename for separator in ("/", "\\")):
        raise LoggingProfileValidationError(
            f"logging profile filename must be a file name, not a path: {filename!r}"
        )
    return filename


def require_bool(value: Any, field_name: str) -> bool:
    """Parse strict boolean-style config values."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise LoggingProfileValidationError(
        f"logging profile field {field_name!r} must be a boolean"
    )


def require_non_empty_text(value: Any, field_name: str) -> str:
    """Return stripped text or raise a field-specific validation error."""

    text = str(value).strip()
    if not text:
        raise LoggingProfileValidationError(
            f"logging profile field {field_name!r} must not be empty"
        )
    return text
