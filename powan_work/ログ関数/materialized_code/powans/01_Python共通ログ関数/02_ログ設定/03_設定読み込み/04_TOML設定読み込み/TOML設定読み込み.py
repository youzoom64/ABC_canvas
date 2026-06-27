# powan_id: node-4978470ccd
# title: TOML設定読み込み
# parent: node-7fa481fd54
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

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


def toml_config(path: str | os.PathLike[str]) -> Config:
    """Load a UTF-8 TOML logging config file into a detached plain dict."""
    if tomllib is None:
        raise RuntimeError("TOML logging config requires Python 3.11+ tomllib")

    config_path = Path(path)
    if config_path.suffix.lower() != ".toml":
        raise ValueError(f"TOML logging config must use .toml, got {config_path.suffix or '<none>'}")

    try:
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OSError(f"failed to read TOML logging config {config_path!s}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:  # type: ignore[union-attr]
        raise ValueError(f"invalid TOML logging config in {config_path!s}: {exc}") from exc

    if not isinstance(loaded, Mapping):
        raise TypeError("TOML logging config must contain a top-level table")
    return _plain_dict(loaded)


def toml_config_text(text: str) -> Config:
    """Load a TOML logging config from text, useful for tests or embedded config."""
    if tomllib is None:
        raise RuntimeError("TOML logging config requires Python 3.11+ tomllib")
    loaded = tomllib.loads(text)
    if not isinstance(loaded, Mapping):
        raise TypeError("TOML logging config text must contain a top-level table")
    return _plain_dict(loaded)


def _plain_dict(value: Mapping[str, Any]) -> Config:
    result: Config = {}
    for key, item in value.items():
        result[str(key)] = _plain_dict(item) if isinstance(item, Mapping) else deepcopy(item)
    return result
