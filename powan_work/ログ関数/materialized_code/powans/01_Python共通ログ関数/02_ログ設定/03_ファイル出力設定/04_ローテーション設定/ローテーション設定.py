# powan_id: node-848b29c63c
# title: ローテーション設定
# parent: node-34e4ee95ea
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass
import logging
from logging import Handler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Mapping


class RotationConfigError(ValueError):
    """Raised when log rotation settings cannot be used safely."""


@dataclass(frozen=True)
class RotationConfig:
    """Validated rotation options for standard logging file handlers.

    mode values:
    - "none": use logging.FileHandler without rotation
    - "size": use logging.handlers.RotatingFileHandler
    - "time": use logging.handlers.TimedRotatingFileHandler
    """

    mode: str = "none"
    max_bytes: int = 0
    backup_count: int = 7
    when: str = "midnight"
    interval: int = 1
    utc: bool = False


RotationPolicy = RotationConfig
RotationPolicyConfigError = RotationConfigError


def _setting(settings: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in settings:
            return settings[name]
    return default


def _default_if_blank(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    return value


def _as_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool):
        raise RotationConfigError(f"{name} must be an integer, not a boolean")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RotationConfigError(f"{name} must be an integer: {value!r}") from exc


def _as_bool(value: Any, *, name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "":
            return default
        if normalized in {"1", "true", "yes", "y", "on", "enable", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", "disable", "disabled"}:
            return False
    raise RotationConfigError(f"{name} must be a boolean-like value: {value!r}")


def _as_when(settings: Mapping[str, Any]) -> str:
    raw_when = _setting(settings, "when", "rotation_when", default=None)
    if raw_when is None:
        return "midnight"
    when = str(raw_when).strip()
    if not when:
        raise RotationConfigError("time rotation requires a non-empty when value")
    return when


def resolve_rotation_config(settings: Mapping[str, Any] | None = None) -> RotationConfig:
    """Build a validated rotation config from dict-like settings."""

    settings = settings or {}
    raw_mode = _default_if_blank(_setting(settings, "rotation", "rotation_mode", default="none"), "none")
    if raw_mode is True:
        raw_mode = "size"
    elif raw_mode is False:
        raw_mode = "none"

    mode = str(raw_mode).strip().lower()
    aliases = {
        "off": "none",
        "no": "none",
        "disabled": "none",
        "bytes": "size",
        "file_size": "size",
        "daily": "time",
        "date": "time",
        "timed": "time",
    }
    mode = aliases.get(mode, mode)
    if mode not in {"none", "size", "time"}:
        raise RotationConfigError(f"rotation mode must be one of none, size, or time: {mode!r}")

    max_bytes = _as_int(
        _default_if_blank(_setting(settings, "max_bytes", "rotation_max_bytes", default=0), 0),
        name="max_bytes",
    )
    backup_count = _as_int(
        _default_if_blank(_setting(settings, "backup_count", "retention_count", "keep_files", default=7), 7),
        name="backup_count",
    )
    interval = _as_int(
        _default_if_blank(_setting(settings, "interval", "rotation_interval", default=1), 1),
        name="interval",
    )
    when = _as_when(settings)
    utc = _as_bool(_setting(settings, "utc", "rotation_utc", default=None), name="utc", default=False)

    if max_bytes < 0:
        raise RotationConfigError("max_bytes must be 0 or greater")
    if mode == "size" and max_bytes <= 0:
        raise RotationConfigError("size rotation requires max_bytes greater than 0")
    if backup_count < 0:
        raise RotationConfigError("backup_count must be 0 or greater")
    if interval <= 0:
        raise RotationConfigError("rotation interval must be greater than 0")

    return RotationConfig(
        mode=mode,
        max_bytes=max_bytes,
        backup_count=backup_count,
        when=when,
        interval=interval,
        utc=utc,
    )


def parse_rotation_policy(settings: Mapping[str, Any] | None = None) -> RotationConfig:
    """Backward-compatible alias for resolve_rotation_config."""

    return resolve_rotation_config(settings)


def create_rotation_file_handler(
    path: str | Path,
    rotation: RotationConfig,
    *,
    encoding: str = "utf-8",
    delay: bool = True,
    level: int | str = logging.INFO,
    formatter: logging.Formatter | None = None,
) -> Handler:
    """Create the standard logging handler that matches a rotation config."""

    log_path = Path(path)
    if rotation.mode == "size":
        handler: Handler = RotatingFileHandler(
            log_path,
            maxBytes=rotation.max_bytes,
            backupCount=rotation.backup_count,
            encoding=encoding,
            delay=delay,
        )
    elif rotation.mode == "time":
        handler = TimedRotatingFileHandler(
            log_path,
            when=rotation.when,
            interval=rotation.interval,
            backupCount=rotation.backup_count,
            encoding=encoding,
            delay=delay,
            utc=rotation.utc,
        )
    elif rotation.mode == "none":
        handler = logging.FileHandler(log_path, encoding=encoding, delay=delay)
    else:
        raise RotationConfigError(f"unknown validated rotation mode: {rotation.mode!r}")

    handler.setLevel(level)
    if formatter is not None:
        handler.setFormatter(formatter)
    return handler


def build_rotation_handler(
    path: str | Path,
    settings: Mapping[str, Any] | None = None,
    *,
    encoding: str = "utf-8",
    delay: bool = True,
    level: int | str = logging.INFO,
    formatter: logging.Formatter | None = None,
) -> Handler:
    """Resolve rotation settings and create the matching logging handler."""

    rotation = resolve_rotation_config(settings)
    return create_rotation_file_handler(
        path,
        rotation,
        encoding=encoding,
        delay=delay,
        level=level,
        formatter=formatter,
    )
