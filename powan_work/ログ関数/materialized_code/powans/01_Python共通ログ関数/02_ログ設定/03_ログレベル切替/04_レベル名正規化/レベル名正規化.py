# powan_id: node-cf3b8cb474
# title: レベル名正規化
# parent: node-5411088125
# powanKind: organ
# codeLanguage: python

"""Canonical log-level name normalization utilities.

This organ powan focuses only on log-level *names*. It turns user-facing
strings such as ``trace``, ``DBG``, ``warn-level``, and ``fatal`` into the
canonical names expected by the standard :mod:`logging` ecosystem and by this
project's sibling powans. TRACE registration and name-to-integer conversion are
kept outside this module on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Final, Iterable, Mapping, Sequence

TRACE_NAME: Final[str] = "TRACE"
DEFAULT_LEVEL_NAME: Final[str] = "INFO"
_SEPARATOR_RE: Final[re.Pattern[str]] = re.compile(r"[\s_\-]+")


class LogLevelNameError(ValueError):
    """Raised when a log-level name cannot be normalized."""


class LogLevelName(str, Enum):
    """Canonical log-level names produced by this normalizer."""

    TRACE = TRACE_NAME
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class LogLevelNameSpec:
    """Structured normalization result for config builders and UIs.

    ``raw`` keeps the exact user/config value for diagnostics. ``cleaned`` is
    the separator-insensitive lookup key. ``name`` is the canonical level name
    that later powans can convert to a logging integer. ``used_default`` marks
    permissive fallback behavior so strict and forgiving callers can share the
    same return shape.
    """

    name: str
    raw: object
    cleaned: str
    used_default: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""

        return {
            "name": self.name,
            "raw": self.raw,
            "cleaned": self.cleaned,
            "usedDefault": self.used_default,
        }


@dataclass(frozen=True, slots=True)
class LogLevelNameOptions:
    """Options for reading a level name from flexible app settings."""

    default: str = DEFAULT_LEVEL_NAME
    allow_default_markers: bool = True
    missing_uses_default: bool = True
    invalid_uses_default: bool = False

    def with_default(self, default: str) -> "LogLevelNameOptions":
        """Return a copy that uses a different fallback name."""

        return replace(self, default=default)


_CANONICAL_NAMES: Final[tuple[str, ...]] = tuple(level.value for level in LogLevelName)

_ALIAS_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("TRACE", LogLevelName.TRACE.value),
    ("TRACELEVEL", LogLevelName.TRACE.value),
    ("TRC", LogLevelName.TRACE.value),
    ("VERBOSE", LogLevelName.TRACE.value),
    ("FINEST", LogLevelName.TRACE.value),
    ("DEBUG", LogLevelName.DEBUG.value),
    ("DEBUGLEVEL", LogLevelName.DEBUG.value),
    ("DBG", LogLevelName.DEBUG.value),
    ("DETAIL", LogLevelName.DEBUG.value),
    ("INFO", LogLevelName.INFO.value),
    ("INFOLEVEL", LogLevelName.INFO.value),
    ("INFORMATION", LogLevelName.INFO.value),
    ("NOTICE", LogLevelName.INFO.value),
    ("WARN", LogLevelName.WARNING.value),
    ("WARNLEVEL", LogLevelName.WARNING.value),
    ("WARNING", LogLevelName.WARNING.value),
    ("WARNINGLEVEL", LogLevelName.WARNING.value),
    ("ERROR", LogLevelName.ERROR.value),
    ("ERRORLEVEL", LogLevelName.ERROR.value),
    ("ERR", LogLevelName.ERROR.value),
    ("EXCEPTION", LogLevelName.ERROR.value),
    ("CRITICAL", LogLevelName.CRITICAL.value),
    ("CRITICALLEVEL", LogLevelName.CRITICAL.value),
    ("CRIT", LogLevelName.CRITICAL.value),
    ("FATAL", LogLevelName.CRITICAL.value),
    ("FATALLEVEL", LogLevelName.CRITICAL.value),
)

_LEVEL_ALIASES: Final[dict[str, str]] = dict(_ALIAS_PAIRS)
_DEFAULT_MARKERS: Final[frozenset[str]] = frozenset({"DEFAULT", "AUTO"})


def supported_log_level_names() -> tuple[str, ...]:
    """Return the canonical names accepted by downstream logging setup."""

    return _CANONICAL_NAMES


def log_level_aliases() -> dict[str, str]:
    """Return a copy of separator-normalized aliases to canonical names."""

    return dict(_LEVEL_ALIASES)


def aliases_for_log_level(canonical_name: object) -> tuple[str, ...]:
    """Return known alias keys for one canonical name."""

    name = normalize_log_level_name(canonical_name)
    return tuple(alias for alias, canonical in _ALIAS_PAIRS if canonical == name)


def default_marker_names() -> tuple[str, ...]:
    """Return markers that can mean "use the configured default"."""

    return tuple(sorted(_DEFAULT_MARKERS))


def _supported_text() -> str:
    return ", ".join(_CANONICAL_NAMES)


def _type_name(value: object) -> str:
    return type(value).__name__


def _ensure_text(value: object, *, field_name: str) -> str:
    if isinstance(value, bool):
        raise LogLevelNameError(
            f"{field_name} must be text, not bool. Use a name such as "
            "'INFO', 'DEBUG', or 'TRACE'."
        )
    if not isinstance(value, str):
        raise LogLevelNameError(
            f"{field_name} must be text, got {_type_name(value)}. "
            f"Supported levels: {_supported_text()}."
        )
    return value


def clean_log_level_key(level_name: object) -> str:
    """Return the uppercase alias lookup key for a raw level string.

    Whitespace, hyphens, and underscores are treated as separators and removed.
    For example, ``" warn-level "``, ``"warn_level"``, and
    ``"WARN LEVEL"`` all become ``"WARNLEVEL"``.
    """

    text = _ensure_text(level_name, field_name="level_name")
    return _SEPARATOR_RE.sub("", text.strip()).upper()


def is_default_marker(level_name: object) -> bool:
    """Return whether a value is an explicit default marker."""

    if not isinstance(level_name, str):
        return False
    return clean_log_level_key(level_name) in _DEFAULT_MARKERS


def is_supported_log_level_name(level_name: object) -> bool:
    """Return whether ``level_name`` can be normalized without raising."""

    try:
        normalize_log_level_name(level_name)
    except LogLevelNameError:
        return False
    return True


def normalize_log_level_name(level_name: object) -> str:
    """Normalize a user-facing log-level name to a canonical string.

    Accepted aliases include ``trace/trc/verbose``, ``debug/dbg``,
    ``info/information``, ``warn/warning``, ``error/err/exception``, and
    ``critical/fatal``. Boolean and non-string values are rejected so that this
    powan remains a clear name-only boundary.
    """

    cleaned = clean_log_level_key(level_name)
    if not cleaned:
        raise LogLevelNameError(
            f"Log level name is empty. Supported levels: {_supported_text()}."
        )

    canonical = _LEVEL_ALIASES.get(cleaned)
    if canonical is None:
        raise LogLevelNameError(
            f"Unknown log level name {level_name!r}. Supported levels: "
            f"{_supported_text()}."
        )
    return canonical


def normalize_log_level_name_spec(level_name: object) -> LogLevelNameSpec:
    """Normalize and return structured data for downstream setting builders."""

    cleaned = clean_log_level_key(level_name)
    name = normalize_log_level_name(level_name)
    return LogLevelNameSpec(name=name, raw=level_name, cleaned=cleaned)


def normalize_optional_log_level_name(
    level_name: object,
    *,
    default: str = DEFAULT_LEVEL_NAME,
    allow_default_markers: bool = True,
) -> str:
    """Normalize a level name, using ``default`` for ``None`` or markers.

    Empty strings are still invalid because they usually point to a broken env
    var or blank UI field. ``DEFAULT`` and ``AUTO`` are accepted only when the
    caller opts into marker behavior.
    """

    default_name = normalize_log_level_name(default)
    if level_name is None:
        return default_name
    if allow_default_markers and is_default_marker(level_name):
        return default_name
    return normalize_log_level_name(level_name)


def normalize_log_level_name_or_default(
    level_name: object,
    *,
    default: str = DEFAULT_LEVEL_NAME,
) -> LogLevelNameSpec:
    """Normalize a name, falling back to ``default`` on invalid input."""

    default_name = normalize_log_level_name(default)
    try:
        return normalize_log_level_name_spec(level_name)
    except LogLevelNameError:
        cleaned = clean_log_level_key(level_name) if isinstance(level_name, str) else ""
        return LogLevelNameSpec(
            name=default_name,
            raw=level_name,
            cleaned=cleaned,
            used_default=True,
        )


def normalize_many_log_level_names(level_names: Iterable[object]) -> tuple[str, ...]:
    """Normalize a sequence of names while preserving order."""

    if isinstance(level_names, (str, bytes)) or not isinstance(level_names, Iterable):
        raise LogLevelNameError(
            "level_names must be an iterable of log-level name values, not a "
            f"single {_type_name(level_names)}."
        )
    return tuple(normalize_log_level_name(value) for value in level_names)


def normalize_unique_log_level_names(level_names: Iterable[object]) -> tuple[str, ...]:
    """Normalize names and remove duplicates while preserving first use."""

    seen: set[str] = set()
    normalized: list[str] = []
    for name in normalize_many_log_level_names(level_names):
        if name not in seen:
            seen.add(name)
            normalized.append(name)
    return tuple(normalized)


def read_log_level_name_from_mapping(
    settings: Mapping[str, object],
    *,
    key: str = "level",
    options: LogLevelNameOptions | None = None,
) -> LogLevelNameSpec:
    """Read and normalize a level name from a settings mapping."""

    if not isinstance(settings, Mapping):
        raise TypeError(f"settings must be a mapping, got {_type_name(settings)}.")
    if not isinstance(key, str) or not key:
        raise ValueError("key must be a non-empty string.")

    selected = options or LogLevelNameOptions()
    default_name = normalize_log_level_name(selected.default)

    if key not in settings:
        if not selected.missing_uses_default:
            raise LogLevelNameError(f"Missing required log level setting {key!r}.")
        return LogLevelNameSpec(
            name=default_name,
            raw=None,
            cleaned=clean_log_level_key(selected.default),
            used_default=True,
        )

    raw = settings[key]
    try:
        name = normalize_optional_log_level_name(
            raw,
            default=default_name,
            allow_default_markers=selected.allow_default_markers,
        )
        cleaned = clean_log_level_key(raw) if isinstance(raw, str) else ""
        return LogLevelNameSpec(name=name, raw=raw, cleaned=cleaned)
    except LogLevelNameError:
        if not selected.invalid_uses_default:
            raise
        cleaned = clean_log_level_key(raw) if isinstance(raw, str) else ""
        return LogLevelNameSpec(
            name=default_name,
            raw=raw,
            cleaned=cleaned,
            used_default=True,
        )


def normalize_log_level_settings(
    settings: Mapping[str, object],
    *,
    key: str = "level",
    output_key: str | None = None,
    options: LogLevelNameOptions | None = None,
) -> dict[str, object]:
    """Return a copy of settings with one level name normalized."""

    spec = read_log_level_name_from_mapping(settings, key=key, options=options)
    normalized = dict(settings)
    normalized[output_key or key] = spec.name
    normalized[f"{output_key or key}Raw"] = spec.raw
    normalized[f"{output_key or key}UsedDefault"] = spec.used_default
    return normalized


def require_canonical_log_level_name(level_name: object) -> str:
    """Return ``level_name`` only when it is already a canonical name."""

    name = normalize_log_level_name(level_name)
    text = _ensure_text(level_name, field_name="level_name").strip()
    if text != name:
        raise LogLevelNameError(
            f"Log level name {level_name!r} normalizes to {name!r}; expected an "
            "already-canonical name."
        )
    return name


def describe_log_level_name_contract() -> dict[str, object]:
    """Return the public name-normalization contract for help screens."""

    return {
        "canonicalNames": supported_log_level_names(),
        "aliases": log_level_aliases(),
        "default": DEFAULT_LEVEL_NAME,
        "defaultMarkers": default_marker_names(),
        "separatorRule": "spaces, hyphens, and underscores are ignored",
    }


def assert_log_level_names_supported(level_names: Sequence[object]) -> None:
    """Raise a clear error if any name in ``level_names`` is unsupported."""

    normalize_many_log_level_names(level_names)
