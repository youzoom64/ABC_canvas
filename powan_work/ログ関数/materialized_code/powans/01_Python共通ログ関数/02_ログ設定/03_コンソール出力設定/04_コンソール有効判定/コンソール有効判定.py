# powan_id: node-de51b7de78
# title: コンソール有効判定
# parent: node-ef620afdd3
# powanKind: organ
# codeLanguage: python

"""Console enabled decision helpers.

This organ powan answers one narrow question for logging setup:
should a console handler be created?  It accepts loose settings from mappings,
dataclasses, or simple objects, applies a caller default when no explicit value
exists, optionally lets environment variables override config, and gates output
with a development-only flag.

The public boundary is intentionally small:
``console_enabled(...)`` returns the bool that standard logging setup wants,
``resolve_console_enabled(...)`` is a friendly alias for configuration code, and
``decide_console_enabled(...)`` returns a diagnostic dataclass for tests, logs,
or UI validation messages.  Formatter selection and StreamHandler construction
belong to the parent console-output powan, not here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Mapping

TRUE_VALUES = frozenset({"1", "true", "yes", "on", "y", "enabled", "enable"})
FALSE_VALUES = frozenset({"0", "false", "no", "off", "n", "disabled", "disable"})

ENABLED_KEYS = (
    "console_enabled",
    "consoleEnabled",
    "enable_console",
    "enableConsole",
    "console",
    "enabled",
)
DEV_ONLY_KEYS = (
    "console_dev_only",
    "consoleDevOnly",
    "dev_only",
    "devOnly",
    "development_only",
    "developmentOnly",
)
ENVIRONMENT_SETTING_KEYS = (
    "console_env",
    "consoleEnv",
    "environment",
    "env",
    "app_env",
    "appEnv",
)
ENV_ENABLED_KEYS = (
    "LOG_CONSOLE_ENABLED",
    "CONSOLE_LOG_ENABLED",
    "ENABLE_CONSOLE_LOG",
    "PYTHON_LOG_CONSOLE",
)
ENV_DEV_ONLY_KEYS = (
    "LOG_CONSOLE_DEV_ONLY",
    "CONSOLE_LOG_DEV_ONLY",
    "PYTHON_LOG_CONSOLE_DEV_ONLY",
)
ENV_DEVELOPMENT_KEYS = (
    "APP_ENV",
    "ENV",
    "ENVIRONMENT",
    "PYTHON_ENV",
    "NODE_ENV",
)
DEVELOPMENT_VALUES = frozenset({"dev", "develop", "development", "local", "debug", "test", "testing"})
NON_DEVELOPMENT_VALUES = frozenset({"prod", "production", "live", "stage", "staging", "release", "ci"})
MISSING = object()


class ConsoleEnabledDecisionError(ValueError):
    """Raised when console-enabled settings cannot be interpreted."""


@dataclass(frozen=True)
class SettingLookup:
    """A config value plus the key and source that supplied it."""

    value: Any
    key: str | None
    source: str
    defaulted: bool

    def label(self, fallback: str) -> str:
        """Return a field label for errors or explanations."""

        if self.key is None:
            return fallback
        return self.key


@dataclass(frozen=True)
class DevelopmentModeDecision:
    """The development-mode answer used for dev_only gating."""

    is_development: bool
    source: str
    value: Any


@dataclass(frozen=True)
class ConsoleEnabledDecision:
    """Detailed console-enabled decision for logging setup."""

    enabled: bool
    requested_enabled: bool
    default_enabled: bool
    dev_only: bool
    is_development: bool
    source_key: str | None
    source: str
    dev_only_source_key: str | None
    dev_only_source: str
    environment_source: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        """Return a plain diagnostic mapping."""

        return {
            "enabled": self.enabled,
            "requested_enabled": self.requested_enabled,
            "default_enabled": self.default_enabled,
            "dev_only": self.dev_only,
            "is_development": self.is_development,
            "source_key": self.source_key,
            "source": self.source,
            "dev_only_source_key": self.dev_only_source_key,
            "dev_only_source": self.dev_only_source,
            "environment_source": self.environment_source,
            "reason": self.reason,
        }


def console_enabled(
    settings: Mapping[str, Any] | Any | None = None,
    *,
    default: bool | int | str = True,
    is_development: bool | int | str | None = None,
    env: Mapping[str, str] | None = None,
    allow_env_override: bool = False,
) -> bool:
    """Return the bool needed before creating a standard logging handler."""

    return decide_console_enabled(
        settings,
        default=default,
        is_development=is_development,
        env=env,
        allow_env_override=allow_env_override,
    ).enabled


def resolve_console_enabled(
    settings: Mapping[str, Any] | Any | None = None,
    *,
    default: bool | int | str = True,
    is_development: bool | int | str | None = None,
    env: Mapping[str, str] | None = None,
    allow_env_override: bool = False,
) -> bool:
    """Configuration-friendly alias for ``console_enabled``."""

    return console_enabled(
        settings,
        default=default,
        is_development=is_development,
        env=env,
        allow_env_override=allow_env_override,
    )


def decide_console_enabled(
    settings: Mapping[str, Any] | Any | None = None,
    *,
    default: bool | int | str = True,
    is_development: bool | int | str | None = None,
    env: Mapping[str, str] | None = None,
    allow_env_override: bool = False,
) -> ConsoleEnabledDecision:
    """Return the final enabled decision with a compact reason."""

    environment = env if env is not None else os.environ
    default_enabled = parse_config_bool(default, field_name="default")
    enabled_lookup = read_setting(
        settings,
        ENABLED_KEYS,
        default=default_enabled,
        env=environment,
        env_keys=ENV_ENABLED_KEYS,
        allow_env_override=allow_env_override,
    )
    requested_enabled = parse_config_bool(
        enabled_lookup.value,
        field_name=enabled_lookup.label("console_enabled"),
    )

    dev_only_lookup = read_setting(
        settings,
        DEV_ONLY_KEYS,
        default=False,
        env=environment,
        env_keys=ENV_DEV_ONLY_KEYS,
        allow_env_override=allow_env_override,
    )
    dev_only = parse_config_bool(
        dev_only_lookup.value,
        field_name=dev_only_lookup.label("console_dev_only"),
    )

    development = resolve_development_mode_decision(
        settings,
        is_development=is_development,
        env=environment,
    )
    enabled = requested_enabled and (development.is_development if dev_only else True)
    reason = build_reason(
        enabled=enabled,
        requested_enabled=requested_enabled,
        default_enabled=default_enabled,
        enabled_lookup=enabled_lookup,
        dev_only=dev_only,
        dev_only_lookup=dev_only_lookup,
        development=development,
    )

    return ConsoleEnabledDecision(
        enabled=enabled,
        requested_enabled=requested_enabled,
        default_enabled=default_enabled,
        dev_only=dev_only,
        is_development=development.is_development,
        source_key=enabled_lookup.key,
        source=enabled_lookup.source,
        dev_only_source_key=dev_only_lookup.key,
        dev_only_source=dev_only_lookup.source,
        environment_source=development.source,
        reason=reason,
    )


def read_setting(
    settings: Mapping[str, Any] | Any | None,
    keys: tuple[str, ...],
    *,
    default: Any,
    env: Mapping[str, str],
    env_keys: tuple[str, ...],
    allow_env_override: bool,
) -> SettingLookup:
    """Read settings first, then optional environment override."""

    lookup = lookup_setting(settings, keys, default=default)
    if allow_env_override:
        env_value = first_mapping_value(env, env_keys, default=MISSING)
        if env_value.key is not None:
            return env_value
    return lookup


def lookup_setting(settings: Mapping[str, Any] | Any | None, keys: tuple[str, ...], *, default: Any) -> SettingLookup:
    """Read the first matching key from mapping, dataclass, get-method, or attributes."""

    if settings is None:
        return SettingLookup(default, None, "default", True)

    mapping = dataclass_to_mapping(settings) if not isinstance(settings, Mapping) else settings
    if mapping is not None:
        found = first_mapping_value(mapping, keys, default=MISSING, source_name="settings")
        if found.key is not None:
            return found

    getter = getattr(settings, "get", None)
    if callable(getter):
        for key in keys:
            value = getter(key, MISSING)
            if value is not MISSING:
                return SettingLookup(value, key, "settings", False)

    for key in keys:
        if hasattr(settings, key):
            return SettingLookup(getattr(settings, key), key, "settings", False)

    return SettingLookup(default, None, "default", True)


def dataclass_to_mapping(value: Any) -> dict[str, Any] | None:
    """Return dataclass field values without deep-copying nested values."""

    if not is_dataclass(value) or isinstance(value, type):
        return None
    return {field.name: getattr(value, field.name) for field in fields(value)}


def first_mapping_value(
    source: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    default: Any,
    source_name: str = "environment",
    source_label: str | None = None,
) -> SettingLookup:
    """Return the first present mapping key while preserving falsy values."""

    origin = source_label if source_label is not None else source_name
    for key in keys:
        if key in source:
            return SettingLookup(source[key], key, origin, False)
    return SettingLookup(default, None, "default", True)


def parse_config_bool(value: Any, *, field_name: str) -> bool:
    """Parse common boolean-like config values with clear errors."""

    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    clean = str(value).strip().lower()
    if clean in TRUE_VALUES:
        return True
    if clean in FALSE_VALUES:
        return False
    if clean == "":
        raise ConsoleEnabledDecisionError(f"{field_name} cannot be an empty string.")

    accepted = ", ".join(sorted(TRUE_VALUES | FALSE_VALUES))
    raise ConsoleEnabledDecisionError(
        f"{field_name} must be a boolean-like value, got {value!r}. Accepted values: {accepted}."
    )


def resolve_development_mode(
    settings: Mapping[str, Any] | Any | None = None,
    *,
    is_development: bool | int | str | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Return whether runtime should count as development."""

    return resolve_development_mode_decision(settings, is_development=is_development, env=env).is_development


def resolve_development_mode_decision(
    settings: Mapping[str, Any] | Any | None = None,
    *,
    is_development: bool | int | str | None = None,
    env: Mapping[str, str] | None = None,
) -> DevelopmentModeDecision:
    """Resolve development mode from argument, settings, environment, or default."""

    if is_development is not None:
        parsed = parse_config_bool(is_development, field_name="is_development")
        return DevelopmentModeDecision(parsed, "argument:is_development", is_development)

    setting_env = lookup_setting(settings, ENVIRONMENT_SETTING_KEYS, default=MISSING)
    if setting_env.key is not None and setting_env.value is not MISSING and setting_env.value is not None:
        parsed = parse_environment_name(setting_env.value, field_name=setting_env.key)
        return DevelopmentModeDecision(parsed, f"settings:{setting_env.key}", setting_env.value)

    environment = env if env is not None else os.environ
    for key in ENV_DEVELOPMENT_KEYS:
        value = environment.get(key)
        if value is not None and str(value).strip() != "":
            parsed = parse_environment_name(value, field_name=key)
            return DevelopmentModeDecision(parsed, f"env:{key}", value)

    return DevelopmentModeDecision(False, "default:false", None)


def parse_environment_name(value: Any, *, field_name: str) -> bool:
    """Interpret an environment name or boolean-like value as development mode."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    clean = str(value).strip().lower()
    if clean in DEVELOPMENT_VALUES:
        return True
    if clean in NON_DEVELOPMENT_VALUES:
        return False
    if clean in TRUE_VALUES:
        return True
    if clean in FALSE_VALUES:
        return False
    if clean == "":
        raise ConsoleEnabledDecisionError(f"{field_name} cannot be an empty environment value.")

    dev_values = ", ".join(sorted(DEVELOPMENT_VALUES))
    non_dev_values = ", ".join(sorted(NON_DEVELOPMENT_VALUES))
    raise ConsoleEnabledDecisionError(
        f"{field_name} must name a known environment or boolean-like value, got {value!r}. "
        f"Development values: {dev_values}. Non-development values: {non_dev_values}."
    )


def build_reason(
    *,
    enabled: bool,
    requested_enabled: bool,
    default_enabled: bool,
    enabled_lookup: SettingLookup,
    dev_only: bool,
    dev_only_lookup: SettingLookup,
    development: DevelopmentModeDecision,
) -> str:
    """Build a compact explanation for tests, logs, and config UIs."""

    enabled_part = f"{enabled_lookup.key}={requested_enabled}" if enabled_lookup.key else f"default={default_enabled}"
    dev_part = f"{dev_only_lookup.key}={dev_only}" if dev_only_lookup.key else f"dev_only={dev_only}"
    if not dev_only:
        return f"console enabled is {enabled}: {enabled_part}, {dev_part}."

    mode = "development" if development.is_development else "non-development"
    return f"console enabled is {enabled}: {enabled_part}, {dev_part}, runtime={mode} via {development.source}."


def validate_console_enabled_settings(settings: Mapping[str, Any] | Any | None = None) -> list[str]:
    """Return validation errors instead of raising."""

    errors: list[str] = []
    for keys, default, label in (
        (ENABLED_KEYS, True, "console_enabled"),
        (DEV_ONLY_KEYS, False, "console_dev_only"),
    ):
        lookup = lookup_setting(settings, keys, default=default)
        try:
            parse_config_bool(lookup.value, field_name=lookup.label(label))
        except ConsoleEnabledDecisionError as exc:
            errors.append(str(exc))

    env_lookup = lookup_setting(settings, ENVIRONMENT_SETTING_KEYS, default=MISSING)
    if env_lookup.key is not None and env_lookup.value is not MISSING and env_lookup.value is not None:
        try:
            parse_environment_name(env_lookup.value, field_name=env_lookup.key)
        except ConsoleEnabledDecisionError as exc:
            errors.append(str(exc))
    return errors


def require_valid_console_enabled_settings(settings: Mapping[str, Any] | Any | None = None) -> None:
    """Raise one clear error if any console-enabled settings are invalid."""

    errors = validate_console_enabled_settings(settings)
    if errors:
        raise ConsoleEnabledDecisionError("; ".join(errors))


def accepted_boolean_values() -> tuple[str, ...]:
    """Return accepted boolean text values for config help."""

    return tuple(sorted(TRUE_VALUES | FALSE_VALUES))


def accepted_development_values() -> tuple[str, ...]:
    """Return environment names treated as development."""

    return tuple(sorted(DEVELOPMENT_VALUES))


def accepted_non_development_values() -> tuple[str, ...]:
    """Return environment names treated as non-development."""

    return tuple(sorted(NON_DEVELOPMENT_VALUES))
