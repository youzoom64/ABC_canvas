# powan_id: node-f241dbce6f
# title: ファイル設定読み込み
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

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None  # type: ignore[assignment]


Config = dict[str, Any]


def file_config(path: str | os.PathLike[str]) -> Config:
    """Load a UTF-8 JSON or TOML logging config file as a plain dict.

    Supported extensions are .json and .toml. TOML loading uses Python 3.11+'s
    tomllib. The loaded top-level value must be a mapping because logging
    configuration is expected to be dictionary-shaped.
    """
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


def _plain_dict(value: Mapping[str, Any]) -> Config:
    """Return a defensive copy using builtin dicts and string keys."""
    result: Config = {}
    for key, item in value.items():
        result[str(key)] = _plain_dict(item) if isinstance(item, Mapping) else deepcopy(item)
    return result
