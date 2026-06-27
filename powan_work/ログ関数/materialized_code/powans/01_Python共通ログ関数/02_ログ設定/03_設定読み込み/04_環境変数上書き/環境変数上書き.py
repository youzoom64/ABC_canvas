# powan_id: node-2d362422cb
# title: 環境変数上書き
# parent: node-7fa481fd54
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Callable


Config = dict[str, Any]
EnvCaster = Callable[[str], Any]

_TRUE_VALUES = {"1", "true", "yes", "on", "y"}
_FALSE_VALUES = {"0", "false", "no", "off", "n"}


def env_override_config(
    *,
    environ: Mapping[str, str] | None = None,
    prefix: str = "LOG_",
) -> Config:
    """Convert LOG_* variables into a logging override dictionary.

    Empty environment values are ignored so they do not erase existing config.
    Boolean values must be explicit truthy/falsy text; invalid booleans raise
    ValueError to make a bad deployment setting visible immediately.
    """
    env = os.environ if environ is None else environ
    overrides: Config = {}
    mapping: dict[str, tuple[str, EnvCaster]] = {
        "LEVEL": ("level", _as_text),
        "PATH": ("path", _as_text),
        "FILE": ("file", _as_bool),
        "CONSOLE": ("console", _as_bool),
        "FORMAT": ("format", _as_text),
        "MAX_BYTES": ("max_bytes", _as_int),
        "BACKUP_COUNT": ("backup_count", _as_int),
    }

    for suffix, (target_key, caster) in mapping.items():
        raw_value = env.get(_env_key(prefix, suffix))
        if raw_value is None or raw_value == "":
            continue
        overrides[target_key] = caster(raw_value)

    return overrides


def _env_key(prefix: str, suffix: str) -> str:
    return f"{prefix}{suffix}" if prefix else suffix


def _as_text(value: str) -> str:
    return value.strip()


def _as_int(value: str) -> int:
    return int(value.strip())


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")
