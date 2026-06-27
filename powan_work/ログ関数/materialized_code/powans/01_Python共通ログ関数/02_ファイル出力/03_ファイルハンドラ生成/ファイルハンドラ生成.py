# powan_id: node-82cb45e7df
# title: ファイルハンドラ生成
# parent: node-92b7df4887
# powanKind: nerve
# codeLanguage: python

import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, Optional


def build_file_handler(path: str | Path, *, formatter: Optional[logging.Formatter] = None, level: int = logging.INFO, encoding: str = "utf-8", rotation: Mapping[str, Any] | None = None) -> logging.Handler:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    rotation = dict(rotation or {})
    mode = str(rotation.get("mode", "none")).lower()
    if mode == "size":
        handler: logging.Handler = RotatingFileHandler(path, maxBytes=int(rotation.get("max_bytes", 10 * 1024 * 1024)), backupCount=int(rotation.get("backup_count", 7)), encoding=encoding)
    elif mode in {"time", "daily"}:
        handler = TimedRotatingFileHandler(path, when=str(rotation.get("when", "midnight")), interval=int(rotation.get("interval", 1)), backupCount=int(rotation.get("backup_count", 7)), encoding=encoding, utc=bool(rotation.get("utc", False)))
    else:
        handler = logging.FileHandler(path, encoding=encoding)
    handler.setLevel(level)
    if formatter is not None:
        handler.setFormatter(formatter)
    return handler
