# powan_id: node-a44683e550
# title: タイムスタンプ有無判定
# parent: node-14cf6a99bc
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any, Mapping


_TIMESTAMP_STYLE_TOKENS = frozenset({
    "timestamp",
    "time",
    "timed",
    "datetime",
    "date-time",
    "iso-time",
    "with-time",
    "with-timestamp",
    "timestamp-dev",
    "dev-timestamp",
})

_NO_TIMESTAMP_STYLE_TOKENS = frozenset({
    "compact",
    "simple",
    "short",
    "default",
    "plain",
    "dev",
    "debug",
    "without-time",
    "without-timestamp",
    "no-time",
    "no-timestamp",
})

_TIMESTAMP_CONFIG_KEYS = (
    "include_timestamp",
    "timestamp",
    "timestamps",
    "show_timestamp",
    "show_timestamps",
    "console_timestamp",
    "console_timestamps",
    "console_include_timestamp",
    "log_timestamp",
    "log_timestamps",
)

_STYLE_CONFIG_KEYS = (
    "console_style",
    "console_format",
    "format_style",
    "style",
    "mode",
    "display_mode",
)

_TRUE_STRINGS = frozenset({"1", "true", "yes", "on", "y", "t", "enable", "enabled"})
_FALSE_STRINGS = frozenset({"0", "false", "no", "off", "n", "f", "disable", "disabled", "none", "null", ""})


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _coerce_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUE_STRINGS:
            return True
        if token in _FALSE_STRINGS:
            return False
    return None


def _style_mentions_timestamp(style: Any) -> bool | None:
    token = _normalize_token(style)
    if not token:
        return None
    if token in _TIMESTAMP_STYLE_TOKENS:
        return True
    if token in _NO_TIMESTAMP_STYLE_TOKENS:
        return False
    parts = {part for part in token.replace(":", "-").split("-") if part}
    if {"no", "timestamp"}.issubset(parts) or {"without", "timestamp"}.issubset(parts):
        return False
    if "timestamp" in parts or "time" in parts:
        return True
    return None


def should_include_console_timestamp(
    style: Any = None,
    *,
    include_timestamp: bool | None = None,
    config: Mapping[str, Any] | None = None,
    default: bool = False,
) -> bool:
    """Return whether the console log format should include a timestamp.

    Explicit include_timestamp wins first, then timestamp-like config keys,
    then timestamp-flavored style or mode names. Unknown values fall back to
    default so compact console output stays quiet unless asked otherwise.
    """
    explicit = _coerce_optional_bool(include_timestamp)
    if explicit is not None:
        return explicit

    if config:
        for key in _TIMESTAMP_CONFIG_KEYS:
            if key in config:
                configured = _coerce_optional_bool(config[key])
                if configured is not None:
                    return configured

        for key in _STYLE_CONFIG_KEYS:
            if key in config:
                style_choice = _style_mentions_timestamp(config[key])
                if style_choice is not None:
                    return style_choice

    style_choice = _style_mentions_timestamp(style)
    if style_choice is not None:
        return style_choice

    return bool(default)


def console_timestamp_enabled(*args: Any, **kwargs: Any) -> bool:
    """Alias for callers that prefer an enabled/disabled predicate name."""
    return should_include_console_timestamp(*args, **kwargs)


__all__ = [
    "console_timestamp_enabled",
    "should_include_console_timestamp",
]
