# powan_id: node-da4b7f9190
# title: JSON設定読み込み
# parent: node-7fa481fd54
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any


Config = dict[str, Any]


def json_config(path: str | os.PathLike[str]) -> Config:
    """Load a UTF-8 JSON logging config file into a detached plain dict."""
    config_path = Path(path)
    if config_path.suffix.lower() != ".json":
        raise ValueError(f"JSON logging config must use .json, got {config_path.suffix or '<none>'}")

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OSError(f"failed to read JSON logging config {config_path!s}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON logging config in {config_path!s}: {exc}") from exc

    if not isinstance(loaded, Mapping):
        raise TypeError("JSON logging config must contain a top-level object")
    return _plain_dict(loaded)


def json_config_text(text: str) -> Config:
    """Load a JSON logging config from text, useful for tests or embedded config."""
    loaded = json.loads(text)
    if not isinstance(loaded, Mapping):
        raise TypeError("JSON logging config text must contain a top-level object")
    return _plain_dict(loaded)


def _plain_dict(value: Mapping[str, Any]) -> Config:
    result: Config = {}
    for key, item in value.items():
        result[str(key)] = _plain_dict(item) if isinstance(item, Mapping) else deepcopy(item)
    return result
