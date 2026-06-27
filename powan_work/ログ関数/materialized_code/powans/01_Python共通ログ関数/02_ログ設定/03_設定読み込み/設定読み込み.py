# powan_id: node-7fa481fd54
# title: 設定読み込み
# parent: node-a3e5f7eb89
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, MutableMapping
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None  # type: ignore[assignment]


Config = dict[str, Any]
EnvCaster = Callable[[str], Any]
EnvSpec = str | tuple[str, EnvCaster]
EnvMap = Mapping[str, EnvSpec]


def load_logging_config(
    *,
    default: Mapping[str, Any] | None = None,
    app: Mapping[str, Any] | str | os.PathLike[str] | None = None,
    env_prefix: str = "LOG_",
    environ: Mapping[str, str] | None = None,
    env_map: EnvMap | None = None,
) -> Config:
    """Return a final logging config from defaults, app config, and env overrides.

    Merge order is default -> application -> environment. Later layers win,
    nested mappings are deep-merged, and the returned dict is detached from all
    caller-owned input objects. The shape intentionally stays plain so other
    logging powans can adapt it into handlers, formatters, or dictConfig data.
    """
    if app is None:
        app_config: Config = {}
    elif isinstance(app, (str, os.PathLike)):
        app_config = file_config(app)
    else:
        app_config = dict_config(app)

    env_config = env_override_config(
        environ=environ,
        prefix=env_prefix,
        env_map=env_map,
    )
    return merge_config(default, app_config, env_config)


def dict_config(value: Mapping[str, Any] | None) -> Config:
    """Convert a mapping into a defensive plain dict with string keys."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"logging config must be a mapping, got {type(value).__name__}")
    return _plain_dict(value)


def file_config(path: str | os.PathLike[str]) -> Config:
    """Read a UTF-8 JSON or TOML logging config file as a plain dict."""
    config_path = Path(path)
    suffix = config_path.suffix.lower()

    try:
        if suffix == ".json":
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
        elif suffix == ".toml":
            if tomllib is None:
                raise RuntimeError("TOML logging config requires Python 3.11+ tomllib")
            loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"unsupported logging config file type: {suffix or '<none>'}")
    except OSError as exc:
        raise OSError(f"failed to read logging config file {config_path!s}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON logging config in {config_path!s}: {exc}") from exc

    if not isinstance(loaded, Mapping):
        raise TypeError(f"logging config file {config_path!s} must contain a top-level mapping")
    return _plain_dict(loaded)


def env_override_config(
    *,
    environ: Mapping[str, str] | None = None,
    prefix: str = "LOG_",
    env_map: EnvMap | None = None,
) -> Config:
    """Build a nested override config from environment variables.

    Examples: LOG_LEVEL -> {"level": value}, LOG_CONSOLE ->
    {"handlers": {"console": {"enabled": value}}}. Empty variables are
    ignored so deployment templates can leave values blank.
    """
    source = os.environ if environ is None else environ
    overrides: Config = {}

    for env_name, dotted_path, caster in _iter_env_specs(env_map):
        full_name = _env_key(prefix, env_name)
        raw_value = source.get(full_name)
        if raw_value is None or raw_value == "":
            continue
        try:
            set_dotted_value(overrides, dotted_path, caster(raw_value))
        except Exception as exc:  # noqa: BLE001 - keep the failing env key visible.
            raise ValueError(f"invalid logging environment override {full_name}: {exc}") from exc

    return overrides


def merge_config(*configs: Mapping[str, Any] | None) -> Config:
    """Deep-merge configs from left to right without mutating inputs."""
    merged: Config = {}
    for config in configs:
        if config is None:
            continue
        _deep_merge(merged, dict_config(config))
    return merged


def set_dotted_value(target: Config, dotted_path: str, value: Any) -> Config:
    """Place a value at a dotted path, creating dictionaries on the way."""
    parts = [part.strip() for part in dotted_path.split(".") if part.strip()]
    if not parts:
        raise ValueError("dotted path must contain at least one key")

    cursor: Config = target
    for part in parts[:-1]:
        current = cursor.get(part)
        if current is None:
            next_cursor: Config = {}
            cursor[part] = next_cursor
            cursor = next_cursor
        elif isinstance(current, dict):
            cursor = current
        else:
            raise ValueError(f"cannot place nested value below non-dict key {part!r}")

    cursor[parts[-1]] = deepcopy(value)
    return target


def default_env_map() -> dict[str, EnvSpec]:
    """Return the standard LOG_* to logging-config mapping."""
    return {
        "LEVEL": "level",
        "PATH": "path",
        "FILE": ("handlers.file.enabled", _parse_env_value),
        "CONSOLE": ("handlers.console.enabled", _parse_env_value),
        "FORMAT": "format",
        "MAX_BYTES": ("handlers.file.max_bytes", _parse_env_value),
        "BACKUP_COUNT": ("handlers.file.backup_count", _parse_env_value),
    }


def _iter_env_specs(env_map: EnvMap | None):
    for env_name, spec in (env_map or default_env_map()).items():
        if isinstance(spec, tuple):
            dotted_path, caster = spec
        else:
            dotted_path, caster = spec, _parse_env_value
        yield str(env_name), str(dotted_path), caster


def _env_key(prefix: str, env_name: str) -> str:
    return env_name if prefix and env_name.startswith(prefix) else f"{prefix}{env_name}"


def _deep_merge(base: MutableMapping[str, Any], override: Mapping[str, Any]) -> None:
    for key, value in override.items():
        current = base.get(key)
        if isinstance(current, MutableMapping) and isinstance(value, Mapping):
            _deep_merge(current, value)
        else:
            base[key] = deepcopy(value)


def _plain_dict(value: Mapping[str, Any]) -> Config:
    result: Config = {}
    for key, item in value.items():
        result[str(key)] = _plain_dict(item) if isinstance(item, Mapping) else deepcopy(item)
    return result


def _parse_env_value(value: str) -> Any:
    text = value.strip()
    lowered = text.lower()

    if lowered in {"1", "true", "yes", "on", "y"}:
        return True
    if lowered in {"0", "false", "no", "off", "n"}:
        return False
    if lowered in {"none", "null"}:
        return None

    try:
        return int(text, 10)
    except ValueError:
        pass

    try:
        return float(text)
    except ValueError:
        return text
