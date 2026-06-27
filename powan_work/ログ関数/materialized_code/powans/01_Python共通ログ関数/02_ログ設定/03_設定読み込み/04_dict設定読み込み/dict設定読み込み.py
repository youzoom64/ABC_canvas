# powan_id: node-29c2a512d5
# title: dict設定読み込み
# parent: node-7fa481fd54
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


Config = dict[str, Any]


def dict_config(value: Mapping[str, Any] | None) -> Config:
    """Convert a mapping logging config into a detached plain dict."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"logging config must be a mapping, got {type(value).__name__}")
    return _plain_dict(value)


def _plain_dict(value: Mapping[str, Any]) -> Config:
    result: Config = {}
    for key, item in value.items():
        text_key = str(key)
        result[text_key] = _plain_dict(item) if isinstance(item, Mapping) else deepcopy(item)
    return result
