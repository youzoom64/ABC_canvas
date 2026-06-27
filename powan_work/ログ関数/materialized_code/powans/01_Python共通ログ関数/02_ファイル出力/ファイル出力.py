# powan_id: node-92b7df4887
# title: ファイル出力
# parent: node-704b909f82
# powanKind:
# codeLanguage: python

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, Optional
import re

_SAFE_FILE_STEM = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class FileOutputConfig:
    enabled: bool = True
    directory: str | Path = "logs"
    app_name: str = "app"
    dated_filename: bool = False
    encoding: str = "utf-8"
    level: int = logging.INFO
    rotation_mode: str = "none"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 7
    when: str = "midnight"
    interval: int = 1
    retention_days: Optional[int] = None


def is_file_output_enabled(config: Mapping[str, Any] | bool | None, default: bool = True) -> bool:
    if config is None:
        return default
    if isinstance(config, bool):
        return config
    for key in ("file_enabled", "enable_file", "log_to_file", "file", "enabled"):
        if isinstance(config, Mapping) and key in config:
            value = config[key]
            if isinstance(value, str):
                return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}
            return bool(value)
    return default


def resolve_log_directory(directory: str | Path = "logs") -> Path:
    path = Path(directory).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_log_filename(app_name: str = "app", *, dated: bool = False, suffix: str = ".log") -> str:
    stem = _SAFE_FILE_STEM.sub("_", (app_name or "app").strip()).strip("._-") or "app"
    if dated:
        stem = f"{stem}_{datetime.now():%Y%m%d}"
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return str(Path(stem).with_suffix(suffix))


def log_file_path(config: FileOutputConfig) -> Path:
    return resolve_log_directory(config.directory) / make_log_filename(
        config.app_name,
        dated=config.dated_filename,
    )


def build_file_handler(
    config: FileOutputConfig,
    formatter: logging.Formatter | None = None,
) -> logging.Handler | None:
    if not config.enabled:
        return None
    path = log_file_path(config)
    mode = (config.rotation_mode or "none").lower()
    if mode == "size":
        handler: logging.Handler = RotatingFileHandler(
            path,
            maxBytes=max(1, int(config.max_bytes)),
            backupCount=max(0, int(config.backup_count)),
            encoding=config.encoding or "utf-8",
        )
    elif mode in {"time", "daily"}:
        handler = TimedRotatingFileHandler(
            path,
            when=config.when or "midnight",
            interval=max(1, int(config.interval)),
            backupCount=max(0, int(config.backup_count)),
            encoding=config.encoding or "utf-8",
        )
    else:
        handler = logging.FileHandler(path, encoding=config.encoding or "utf-8")
    handler.setLevel(config.level)
    if formatter is not None:
        handler.setFormatter(formatter)
    return handler


def cleanup_old_logs(directory: str | Path, *, days: int, pattern: str = "*.log") -> list[Path]:
    cutoff = datetime.now().timestamp() - timedelta(days=max(0, int(days))).total_seconds()
    removed: list[Path] = []
    for path in Path(directory).glob(pattern):
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path)
    return removed


def prepare_file_output(
    config: FileOutputConfig,
    formatter: logging.Formatter | None = None,
) -> logging.Handler | None:
    handler = build_file_handler(config, formatter=formatter)
    if config.retention_days is not None:
        cleanup_old_logs(resolve_log_directory(config.directory), days=config.retention_days)
    return handler
