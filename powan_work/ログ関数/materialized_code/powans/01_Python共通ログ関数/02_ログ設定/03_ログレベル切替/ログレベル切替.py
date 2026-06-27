# powan_id: node-5411088125
# title: ログレベル切替
# parent: node-a3e5f7eb89
# powanKind: organ
# codeLanguage: python

"""Log-level switching utilities for shared Python applications.

This organ powan converts user-facing level names such as INFO, DEBUG, TRACE,
WARNING, and ERROR into values accepted by the standard :mod:`logging` module.
It is intentionally small enough to reuse across apps, but complete enough for
profile loaders, environment overrides, and later console/file handler setup to
share the same level contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
import logging
from typing import Any, Final, Literal

TRACE_LEVEL: Final[int] = 5
TRACE_NAME: Final[str] = "TRACE"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

UnknownLevelMode = Literal["raise", "default"]
LevelInput = str | int | None


class LogLevelError(ValueError):
    """Raised when a configured log level cannot be converted safely."""


class LogLevelName(str, Enum):
    """Canonical level names supported by this shared logging layer."""

    TRACE = TRACE_NAME
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class LogLevelSpec:
    """Normalized log-level data that other setting powans can compose.

    ``raw`` keeps the original user/config value for diagnostics. ``name`` is
    the canonical display/config name. ``value`` is safe for ``logger.setLevel``
    and handler configuration. ``used_default`` marks fallback behavior so app
    profile validation can warn without crashing when that policy is desired.
    """

    name: str
    value: int
    raw: LevelInput
    used_default: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a plain dict for JSON-ish config merging code."""

        return {
            "name": self.name,
            "value": self.value,
            "raw": self.raw,
            "usedDefault": self.used_default,
        }


@dataclass(frozen=True, slots=True)
class LogLevelOptions:
    """Options for resolving a log-level value from app settings."""

    default: LevelInput = DEFAULT_LOG_LEVEL
    unknown: UnknownLevelMode = "raise"
    allow_none: bool = True

    def with_default(self, default: LevelInput) -> "LogLevelOptions":
        """Return a copy using a different default level."""

        return replace(self, default=default)


_LEVEL_ALIASES: Final[dict[str, str]] = {
    "TRACE": LogLevelName.TRACE.value,
    "TRC": LogLevelName.TRACE.value,
    "VERBOSE": LogLevelName.TRACE.value,
    "DEBUG": LogLevelName.DEBUG.value,
    "DBG": LogLevelName.DEBUG.value,
    "INFO": LogLevelName.INFO.value,
    "INFORMATION": LogLevelName.INFO.value,
    "NOTICE": LogLevelName.INFO.value,
    "WARN": LogLevelName.WARNING.value,
    "WARNING": LogLevelName.WARNING.value,
    "ERROR": LogLevelName.ERROR.value,
    "ERR": LogLevelName.ERROR.value,
    "EXCEPTION": LogLevelName.ERROR.value,
    "CRITICAL": LogLevelName.CRITICAL.value,
    "FATAL": LogLevelName.CRITICAL.value,
}

_LEVEL_VALUES: Final[dict[str, int]] = {
    LogLevelName.TRACE.value: TRACE_LEVEL,
    LogLevelName.DEBUG.value: logging.DEBUG,
    LogLevelName.INFO.value: logging.INFO,
    LogLevelName.WARNING.value: logging.WARNING,
    LogLevelName.ERROR.value: logging.ERROR,
    LogLevelName.CRITICAL.value: logging.CRITICAL,
}

_REGISTERED_TRACE = False


def _supported_names_text() -> str:
    return ", ".join(_LEVEL_VALUES)


def _clean_level_name(level_name: str) -> str:
    """Normalize separators and casing before alias lookup."""

    cleaned = level_name.strip().replace("-", "_").replace(" ", "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.upper()


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def supported_log_levels() -> tuple[str, ...]:
    """Return canonical names accepted by this module."""

    return tuple(_LEVEL_VALUES)


def supported_log_level_values() -> dict[str, int]:
    """Return a copy of the canonical name-to-value mapping."""

    register_trace_level()
    return dict(_LEVEL_VALUES)


def register_trace_level() -> int:
    """Register TRACE with logging and add ``Logger.trace`` once."""

    global _REGISTERED_TRACE
    if _REGISTERED_TRACE:
        return TRACE_LEVEL

    logging.addLevelName(TRACE_LEVEL, TRACE_NAME)

    if not hasattr(logging.Logger, "trace"):

        def trace(
            self: logging.Logger,
            message: object,
            *args: object,
            **kwargs: object,
        ) -> None:
            if self.isEnabledFor(TRACE_LEVEL):
                self._log(TRACE_LEVEL, message, args, **kwargs)

        setattr(logging.Logger, "trace", trace)

    _REGISTERED_TRACE = True
    return TRACE_LEVEL


def normalize_log_level_name(level: LevelInput, *, allow_none: bool = True) -> str:
    """Return the canonical name for a string/int log level.

    ``None`` becomes the default level only when ``allow_none`` is true. Boolean
    values are rejected even though ``bool`` is an ``int`` subclass, because
    accepting ``True`` as level ``1`` would make config mistakes hard to notice.
    """

    register_trace_level()

    if level is None:
        if allow_none:
            return DEFAULT_LOG_LEVEL
        raise LogLevelError(
            f"Log level is required. Supported levels: {_supported_names_text()}."
        )

    if _is_bool(level):
        raise LogLevelError("Log level must be a name or logging integer, not bool.")

    if isinstance(level, int):
        name = logging.getLevelName(level)
        if isinstance(name, str) and name in _LEVEL_VALUES:
            return name
        raise LogLevelError(
            f"Unsupported numeric log level {level!r}. "
            f"Supported levels: {_supported_names_text()}."
        )

    if not isinstance(level, str):
        raise LogLevelError(
            f"Log level must be str, int, or None, got {type(level).__name__}."
        )

    cleaned = _clean_level_name(level)
    if cleaned in {"", "DEFAULT", "AUTO"}:
        if allow_none:
            return DEFAULT_LOG_LEVEL
        raise LogLevelError(
            f"Log level {level!r} is not allowed here. "
            f"Supported levels: {_supported_names_text()}."
        )

    canonical = _LEVEL_ALIASES.get(cleaned)
    if canonical is None:
        raise LogLevelError(
            f"Unknown log level {level!r}. "
            f"Supported levels: {_supported_names_text()}."
        )
    return canonical


def log_level_to_value(level: LevelInput, *, allow_none: bool = True) -> int:
    """Convert a supported level name/int into a logging level value."""

    canonical = normalize_log_level_name(level, allow_none=allow_none)
    return _LEVEL_VALUES[canonical]


def resolve_log_level(
    level: LevelInput,
    *,
    default: LevelInput = DEFAULT_LOG_LEVEL,
    unknown: UnknownLevelMode = "raise",
    allow_none: bool = True,
) -> LogLevelSpec:
    """Resolve a raw app setting into a ``LogLevelSpec``.

    Set ``unknown="default"`` when an application should keep running with a
    safe fallback. Set ``unknown="raise"`` for strict profile validation.
    """

    if unknown not in {"raise", "default"}:
        raise ValueError("unknown must be 'raise' or 'default'.")

    try:
        name = normalize_log_level_name(level, allow_none=allow_none)
        return LogLevelSpec(name=name, value=_LEVEL_VALUES[name], raw=level)
    except LogLevelError:
        if unknown == "raise":
            raise

    default_name = normalize_log_level_name(default, allow_none=True)
    return LogLevelSpec(
        name=default_name,
        value=_LEVEL_VALUES[default_name],
        raw=level,
        used_default=True,
    )


def resolve_log_level_with_options(
    level: LevelInput,
    options: LogLevelOptions | None = None,
) -> LogLevelSpec:
    """Resolve a level using a dataclass options object."""

    selected = options or LogLevelOptions()
    return resolve_log_level(
        level,
        default=selected.default,
        unknown=selected.unknown,
        allow_none=selected.allow_none,
    )


def read_log_level_from_mapping(
    settings: Mapping[str, Any],
    *,
    key: str = "level",
    default: LevelInput = DEFAULT_LOG_LEVEL,
    unknown: UnknownLevelMode = "raise",
    allow_none: bool = True,
) -> LogLevelSpec:
    """Read and resolve a level from merged app settings.

    The returned spec can be passed directly to console/file handler builders as
    ``spec.value`` while profile UIs can show ``spec.name``.
    """

    if not isinstance(settings, Mapping):
        raise TypeError(f"settings must be a mapping, got {type(settings).__name__}.")

    raw_level = settings.get(key, default)
    if _is_bool(raw_level):
        if unknown == "default":
            raw_level = "__invalid_bool__"
        else:
            raise LogLevelError(
                f"Log level setting {key!r} must be a string, int, or None, not bool."
            )

    if raw_level is not None and not isinstance(raw_level, (str, int)):
        if unknown == "default":
            raw_level = "__invalid_type__"
        else:
            raise LogLevelError(
                f"Log level setting {key!r} must be a string, int, or None, "
                f"got {type(raw_level).__name__}."
            )

    return resolve_log_level(
        raw_level,
        default=default,
        unknown=unknown,
        allow_none=allow_none,
    )


def apply_log_level(logger: logging.Logger, level: LevelInput, **kwargs: Any) -> LogLevelSpec:
    """Resolve ``level``, apply it to ``logger``, and return the spec."""

    if not isinstance(logger, logging.Logger):
        raise TypeError(f"logger must be logging.Logger, got {type(logger).__name__}.")

    spec = resolve_log_level(level, **kwargs)
    logger.setLevel(spec.value)
    return spec


def apply_log_level_to_handler(
    handler: logging.Handler,
    level: LevelInput,
    **kwargs: Any,
) -> LogLevelSpec:
    """Resolve ``level``, apply it to a logging handler, and return the spec."""

    if not isinstance(handler, logging.Handler):
        raise TypeError(
            f"handler must be logging.Handler, got {type(handler).__name__}."
        )

    spec = resolve_log_level(level, **kwargs)
    handler.setLevel(spec.value)
    return spec


def level_name_for_display(level: LevelInput, *, allow_none: bool = True) -> str:
    """Return the canonical display name for a configured level."""

    return normalize_log_level_name(level, allow_none=allow_none)


def build_log_level_settings(
    level: LevelInput,
    *,
    default: LevelInput = DEFAULT_LOG_LEVEL,
    unknown: UnknownLevelMode = "raise",
    allow_none: bool = True,
) -> dict[str, object]:
    """Return a dict fragment ready to merge into app logging settings."""

    spec = resolve_log_level(
        level,
        default=default,
        unknown=unknown,
        allow_none=allow_none,
    )
    return {
        "level": spec.name,
        "levelValue": spec.value,
        "levelRaw": spec.raw,
        "levelUsedDefault": spec.used_default,
    }


def merge_log_level_settings(
    base: Mapping[str, Any] | None,
    override: Mapping[str, Any] | None,
    *,
    key: str = "level",
    default: LevelInput = DEFAULT_LOG_LEVEL,
    unknown: UnknownLevelMode = "raise",
) -> dict[str, object]:
    """Merge two setting dicts and normalize their resulting log level."""

    merged: dict[str, object] = {}
    if base:
        merged.update(dict(base))
    if override:
        merged.update(dict(override))

    spec = read_log_level_from_mapping(
        merged,
        key=key,
        default=default,
        unknown=unknown,
    )
    merged[key] = spec.name
    merged[f"{key}Value"] = spec.value
    merged[f"{key}UsedDefault"] = spec.used_default
    return merged


def is_log_level_enabled(configured: LevelInput, event_level: LevelInput) -> bool:
    """Return whether ``event_level`` should pass ``configured`` threshold."""

    configured_value = log_level_to_value(configured)
    event_value = log_level_to_value(event_level)
    return event_value >= configured_value
