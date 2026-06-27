# powan_id: node-e7807a1854
# title: ファイル出力有効判定
# parent: node-34e4ee95ea
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class FileOutputEnabledConfigError(ValueError):
    """Raised when the file-output enabled setting cannot be interpreted."""


_TRUE_TEXT_VALUES = frozenset(
    {
        "1",
        "true",
        "t",
        "yes",
        "y",
        "on",
        "enable",
        "enabled",
    }
)
_FALSE_TEXT_VALUES = frozenset(
    {
        "0",
        "false",
        "f",
        "no",
        "n",
        "off",
        "disable",
        "disabled",
    }
)
_DEFAULT_SETTING_NAMES = (
    "file_enabled",
    "file_output_enabled",
    "enable_file_output",
    "log_to_file",
    "use_file",
    "enabled",
)


def _coerce_default(default: bool) -> bool:
    if isinstance(default, bool):
        return default
    raise FileOutputEnabledConfigError(
        f"file-output enabled default must be a bool, got {type(default).__name__}: {default!r}"
    )


def _coerce_setting_names(setting_names: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if setting_names is None:
        return _DEFAULT_SETTING_NAMES
    if not isinstance(setting_names, (tuple, list)):
        raise FileOutputEnabledConfigError(
            "file-output enabled setting_names must be a tuple/list of setting keys"
        )

    names: list[str] = []
    for raw_name in setting_names:
        name = str(raw_name).strip()
        if not name:
            raise FileOutputEnabledConfigError(
                "file-output enabled setting_names must not contain an empty key"
            )
        names.append(name)
    if not names:
        raise FileOutputEnabledConfigError(
            "file-output enabled setting_names must contain at least one key"
        )
    return tuple(names)


def _coerce_settings(settings: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if settings is None:
        return {}
    if isinstance(settings, Mapping):
        return settings
    raise FileOutputEnabledConfigError(
        f"file-output enabled settings must be a mapping or None, got {type(settings).__name__}"
    )


def _find_first_setting(
    settings: Mapping[str, Any],
    setting_names: tuple[str, ...],
) -> tuple[bool, str, Any]:
    for name in setting_names:
        if name in settings:
            return True, name, settings[name]
    return False, "", None


def _bool_from_text(value: str, *, setting_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE_TEXT_VALUES:
        return True
    if normalized in _FALSE_TEXT_VALUES:
        return False
    if normalized == "":
        raise FileOutputEnabledConfigError(
            f"file-output enabled setting {setting_name!r} must not be an empty string"
        )
    raise FileOutputEnabledConfigError(
        f"file-output enabled setting {setting_name!r} has unsupported text value {value!r}; "
        "expected one of: true/false, yes/no, on/off, enable/disable, 1/0"
    )


def _bool_from_number(value: int | float, *, setting_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value == 1:
        return True
    if value == 0:
        return False
    raise FileOutputEnabledConfigError(
        f"file-output enabled setting {setting_name!r} must be 1 or 0 when numeric, got {value!r}"
    )


def _as_enabled_bool(value: Any, *, default: bool, setting_name: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _bool_from_text(value, setting_name=setting_name)
    if isinstance(value, int):
        return _bool_from_number(value, setting_name=setting_name)
    raise FileOutputEnabledConfigError(
        f"file-output enabled setting {setting_name!r} must be bool, string, 1/0, or None; "
        f"got {type(value).__name__}: {value!r}"
    )


def resolve_file_output_enabled(
    settings: Mapping[str, Any] | None,
    *,
    default: bool = False,
    setting_names: tuple[str, ...] | list[str] | None = None,
) -> bool:
    """Resolve whether standard logging should attach a file handler.

    The function deliberately returns only a bool. Path resolution, rotation,
    and handler construction stay in sibling powans, while this organ decides
    whether those steps should be active.
    """

    resolved_default = _coerce_default(default)
    resolved_settings = _coerce_settings(settings)
    resolved_names = _coerce_setting_names(setting_names)
    found, setting_name, value = _find_first_setting(resolved_settings, resolved_names)
    if not found:
        return resolved_default
    return _as_enabled_bool(value, default=resolved_default, setting_name=setting_name)


def file_output_enabled(
    settings: Mapping[str, Any] | None,
    *,
    default: bool = False,
    setting_names: tuple[str, ...] | list[str] | None = None,
) -> bool:
    """Backward-compatible alias for callers that use the shorter local name."""

    return resolve_file_output_enabled(
        settings,
        default=default,
        setting_names=setting_names,
    )
