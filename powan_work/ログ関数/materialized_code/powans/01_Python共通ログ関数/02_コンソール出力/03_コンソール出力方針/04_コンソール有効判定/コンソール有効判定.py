# powan_id: node-1dd9fa606d
# title: コンソール有効判定
# parent: node-ffda89edb6
# powanKind: organ
# codeLanguage: python

"""Enable/disable decision for standard-library console logging.

This organ answers one question only: should the caller emit log records to a
console stream? It reads already-resolved settings and runtime flags, but it
does not create handlers, configure formatters, or mutate logging state.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from typing import Any


_TRUE_VALUES = {"1", "true", "yes", "on", "enable", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "disable", "disabled"}
_SETTING_KEYS = ("console_enabled", "console", "enable_console", "console_output")
_RUNTIME_DISABLE_KEYS = ("quiet", "silent", "no_console", "disable_console")
_RUNTIME_ENABLE_KEYS = ("force_console", "verbose", "debug")
_ENV_KEYS = ("LOG_CONSOLE", "CONSOLE_LOG", "PYTHON_LOG_CONSOLE")


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return None


def _first_bool(source: Mapping[str, Any] | None, keys: tuple[str, ...]) -> bool | None:
    if not source:
        return None
    for key in keys:
        if key in source:
            parsed = _to_bool(source[key])
            if parsed is not None:
                return parsed
    return None


def _env_bool(environ: Mapping[str, str]) -> bool | None:
    for key in _ENV_KEYS:
        if key in environ:
            parsed = _to_bool(environ[key])
            if parsed is not None:
                return parsed
    return None


def _has_console_stream_handler(logger: logging.Logger | None) -> bool:
    current = logger if logger is not None else logging.getLogger()
    while current is not None:
        for handler in current.handlers:
            if isinstance(handler, logging.StreamHandler):
                stream = getattr(handler, "stream", None)
                if stream in (None, sys.stdout, sys.stderr):
                    return True
        if not current.propagate:
            break
        current = current.parent
    return False


def is_console_output_enabled(
    settings: Mapping[str, Any] | None = None,
    runtime: Mapping[str, Any] | None = None,
    *,
    logger: logging.Logger | None = None,
    environ: Mapping[str, str] | None = None,
    default: bool = True,
) -> bool:
    """Return whether console output should be active for logging.

    Priority is explicit settings, runtime suppress/force flags, environment
    override, existing standard logging console handler, then the caller default.
    Unknown string values are ignored so config validation can stay elsewhere.
    """

    configured = _first_bool(settings, _SETTING_KEYS)
    if configured is not None:
        return configured

    disabled = _first_bool(runtime, _RUNTIME_DISABLE_KEYS)
    if disabled is True:
        return False

    enabled = _first_bool(runtime, _RUNTIME_ENABLE_KEYS)
    if enabled is True:
        return True

    env_enabled = _env_bool(os.environ if environ is None else environ)
    if env_enabled is not None:
        return env_enabled

    if _has_console_stream_handler(logger):
        return True

    return bool(default)
