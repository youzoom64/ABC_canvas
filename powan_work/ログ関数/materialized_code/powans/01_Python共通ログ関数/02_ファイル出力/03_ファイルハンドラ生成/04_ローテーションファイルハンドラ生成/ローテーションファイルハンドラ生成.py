# powan_id: node-8ff058c57a
# title: ローテーションファイルハンドラ生成
# parent: node-82cb45e7df
# powanKind: organ
# codeLanguage: python

import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path


def create_rotating_file_handler(path: str | Path, mode: str = "size", *, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 7, when: str = "midnight", interval: int = 1, encoding: str = "utf-8") -> logging.Handler:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if mode in {"time", "daily"}:
        return TimedRotatingFileHandler(path, when=when, interval=interval, backupCount=backup_count, encoding=encoding)
    return RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding)
