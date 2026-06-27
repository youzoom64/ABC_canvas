# powan_id: node-57a1063179
# title: レベル値変換
# parent: node-5411088125
# powanKind: organ
# codeLanguage: python

"""Convert log-level names into integer values accepted by ``logging``.

This organ powan is the value-conversion boundary for the parent logging-level
switcher. It accepts already-normalized names such as ``TRACE`` and ``INFO``,
practical raw names such as ``warn`` and ``fatal``, or supported logging integer
values, then returns values safe for ``Logger.setLevel`` and handler setup.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
import logging
from typing import Any, Final, Literal

TRACE_LEVEL: Final[int] = 5
TRACE_NAME: Final[str] = "TRACE"
DEFAULT_LEVEL_NAME: Final[str] = "INFO"

LevelInput = str | int | None
UnknownLevelPolicy = Literal["raise", "default"]


class LogLevelValueError(ValueError):
    """Raised when a log-level value cannot be converted safely."""


class LogLevelName(str, Enum):
    """Canonical names that this converter maps to logging integers."""

    TRACE = TRACE_NAME
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class LogLevelValueSpec:
    """Resolved level data for logger, handler, and config builders."""

    name: str
    value: int
    raw: LevelInput
    used_default: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly settings fragment."""

        return {
            "name": self.name,
            "value": self.value,
            "raw": self.raw,
            "usedDefault": self.used_default,
        }


@dataclass(frozen=True, slots=True)
class LogLevelValueOptions:
    """Options for resolving a level from app settings."""

    default: LevelInput = DEFAULT_LEVEL_NAME
    unknown: UnknownLevelPolicy = "raise"
    allow_none: bool = False

    def with_default(self, default: LevelInput) -> "LogLevelValueOptions":
        return replace(self, default=default)


_LEVEL_VALUES: Final[dict[str, int]] = {
    LogLevelName.TRACE.value: TRACE_LEVEL,
    LogLevelName.DEBUG.value: logging.DEBUG,
    LogLevelName.INFO.value: logging.INFO,
    LogLevelName.WARNING.value: logging.WARNING,
    LogLevelName.ERROR.value: logging.ERROR,
    LogLevelName.CRITICAL.value: logging.CRITICAL,
}

_RAW_NAME_ALIASES: Final[dict[str, str]] = {
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

_REGISTERED_TRACE = False


def register_trace_level() -> int:
    """Register TRACE with ``logging`` once and return its numeric value."""

    global _REGISTERED_TRACE
    if _REGISTERED_TRACE:
        return TRACE_LEVEL
    logging.addLevelName(TRACE_LEVEL, TRACE_NAME)
    _REGISTERED_TRACE = True
    return TRACE_LEVEL


def supported_level_names() -> tuple[str, ...]:
    """Return canonical level names accepted by this converter."""

    return tuple(_LEVEL_VALUES)


def supported_level_values() -> dict[str, int]:
    """Return a copy of the canonical name-to-value mapping."""

    register_trace_level()
    return dict(_LEVEL_VALUES)


def _supported_names_text() -> str:
    return ", ".join(supported_level_names())


def _supported_values_text() -> str:
    return ", ".join(str(v) for v in sorted(set(_LEVEL_VALUES.values())))


def _clean_raw_name(level_name: str) -> str:
    cleaned = level_name.strip().replace("-", "_").replace(" ", "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.upper()


def _reject_bool(value: object) -> None:
    if isinstance(value, bool):
        raise LogLevelValueError("Log level must be a name or logging integer, not bool.")


def canonical_level_name(level: LevelInput, *, allow_none: bool = False) -> str:
    """Return a canonical name for a raw name, normalized name, or integer."""

    register_trace_level()
    if level is None:
        if allow_none:
            return DEFAULT_LEVEL_NAME
        raise LogLevelValueError(
            f"Log level is required. Supported levels: {_supported_names_text()}."
        )

    _reject_bool(level)
    if isinstance(level, int):
        for name, value in _LEVEL_VALUES.items():
            if level == value:
                return name
        raise LogLevelValueError(
            f"Unsupported numeric log level {level!r}. "
            f"Supported numeric values: {_supported_values_text()}."
        )

    if not isinstance(level, str):
        raise LogLevelValueError(
            f"Log level must be str, int, or None, got {type(level).__name__}."
        )

    cleaned = _clean_raw_name(level)
    if cleaned in {"", "DEFAULT", "AUTO"}:
        if allow_none:
            return DEFAULT_LEVEL_NAME
        raise LogLevelValueError(
            f"Log level {level!r} is empty or automatic. "
            f"Supported levels: {_supported_names_text()}."
        )

    canonical = _RAW_NAME_ALIASES.get(cleaned)
    if canonical is None:
        raise LogLevelValueError(
            f"Unknown log level {level!r}. Supported levels: {_supported_names_text()}."
        )
    return canonical


def level_name_to_value(level_name: str) -> int:
    """Convert a canonical or raw level name into a logging integer."""

    if not isinstance(level_name, str):
        raise LogLevelValueError(
            f"Log level name must be str, got {type(level_name).__name__}."
        )
    return _LEVEL_VALUES[canonical_level_name(level_name, allow_none=False)]


def log_level_to_value(level: LevelInput, *, allow_none: bool = False) -> int:
    """Convert a supported name/int into a logging integer."""

    return _LEVEL_VALUES[canonical_level_name(level, allow_none=allow_none)]


def resolve_log_level_value(
    level: LevelInput,
    *,
    default: LevelInput = DEFAULT_LEVEL_NAME,
    unknown: UnknownLevelPolicy = "raise",
    allow_none: bool = False,
) -> LogLevelValueSpec:
    """Resolve ``level`` into canonical name, integer value, and diagnostics."""

    if unknown not in {"raise", "default"}:
        raise ValueError("unknown must be 'raise' or 'default'.")

    try:
        name = canonical_level_name(level, allow_none=allow_none)
        return LogLevelValueSpec(name=name, value=_LEVEL_VALUES[name], raw=level)
    except LogLevelValueError:
        if unknown == "raise":
            raise

    default_name = canonical_level_name(default, allow_none=True)
    return LogLevelValueSpec(
        name=default_name,
        value=_LEVEL_VALUES[default_name],
        raw=level,
        used_default=True,
    )


def resolve_log_level_value_with_options(
    level: LevelInput,
    options: LogLevelValueOptions | None = None,
) -> LogLevelValueSpec:
    """Resolve a level using a reusable options dataclass."""

    selected = options or LogLevelValueOptions()
    return resolve_log_level_value(
        level,
        default=selected.default,
        unknown=selected.unknown,
        allow_none=selected.allow_none,
    )


def log_level_to_value_or_default(
    level: LevelInput,
    *,
    default: LevelInput = DEFAULT_LEVEL_NAME,
) -> int:
    """Return a logging integer, falling back to ``default`` when invalid."""

    return resolve_log_level_value(level, default=default, unknown="default").value


def is_supported_level_value(level: object) -> bool:
    """Return whether ``level`` is one of the supported logging integers."""

    register_trace_level()
    return not isinstance(level, bool) and isinstance(level, int) and level in _LEVEL_VALUES.values()


def is_supported_level_name(level: object) -> bool:
    """Return whether ``level`` can be resolved to a supported level name."""

    if not isinstance(level, str):
        return False
    try:
        canonical_level_name(level)
    except LogLevelValueError:
        return False
    return True


def read_level_value_from_mapping(
    settings: Mapping[str, Any],
    *,
    key: str = "level",
    default: LevelInput = DEFAULT_LEVEL_NAME,
    unknown: UnknownLevelPolicy = "raise",
    allow_none: bool = False,
) -> LogLevelValueSpec:
    """Read a level from a settings mapping and resolve it."""

    if not isinstance(settings, Mapping):
        raise TypeError(f"settings must be a mapping, got {type(settings).__name__}.")
    return resolve_log_level_value(
        settings.get(key, default),
        default=default,
        unknown=unknown,
        allow_none=allow_none,
    )


def build_level_value_settings(
    level: LevelInput,
    *,
    default: LevelInput = DEFAULT_LEVEL_NAME,
    unknown: UnknownLevelPolicy = "raise",
    allow_none: bool = False,
) -> dict[str, object]:
    """Return a dict fragment ready for parent logging settings."""

    return resolve_log_level_value(
        level,
        default=default,
        unknown=unknown,
        allow_none=allow_none,
    ).as_dict()


def apply_level_to_logger(
    logger: logging.Logger,
    level: LevelInput,
    **kwargs: Any,
) -> LogLevelValueSpec:
    """Resolve ``level``, apply it to a logger, and return the spec."""

    if not isinstance(logger, logging.Logger):
        raise TypeError(f"logger must be logging.Logger, got {type(logger).__name__}.")
    spec = resolve_log_level_value(level, **kwargs)
    logger.setLevel(spec.value)
    return spec


def apply_level_to_handler(
    handler: logging.Handler,
    level: LevelInput,
    **kwargs: Any,
) -> LogLevelValueSpec:
    """Resolve ``level``, apply it to a handler, and return the spec."""

    if not isinstance(handler, logging.Handler):
        raise TypeError(f"handler must be logging.Handler, got {type(handler).__name__}.")
    spec = resolve_log_level_value(level, **kwargs)
    handler.setLevel(spec.value)
    return spec


def should_emit(configured: LevelInput, event_level: LevelInput) -> bool:
    """Return whether an event level passes a configured threshold."""

    return log_level_to_value(event_level) >= log_level_to_value(configured)
