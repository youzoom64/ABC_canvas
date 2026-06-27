# powan_id: node-c77bb82e67
# title: 設定マージ
# parent: node-7fa481fd54
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from typing import Any


Config = dict[str, Any]


def merge_config(*configs: Mapping[str, Any] | None) -> Config:
    """Deep-merge logging config mappings from left to right.

    ``None`` layers are ignored. Mapping values are recursively merged when the
    existing value is also a mapping; every other value is replaced by the later
    layer. The returned dict is detached from all caller-owned inputs.
    """
    merged: Config = {}
    for config in configs:
        if config is None:
            continue
        if not isinstance(config, Mapping):
            raise TypeError(f"logging config must be a mapping, got {type(config).__name__}")
        _deep_merge(merged, config)
    return merged


def _deep_merge(base: MutableMapping[str, Any], override: Mapping[str, Any]) -> None:
    for key, value in override.items():
        text_key = str(key)
        current = base.get(text_key)
        if isinstance(current, MutableMapping) and isinstance(value, Mapping):
            _deep_merge(current, value)
        else:
            base[text_key] = _copy_config_value(value)


def _copy_config_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_config_value(item) for key, item in value.items()}
    return deepcopy(value)
