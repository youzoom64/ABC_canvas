# powan_id: node-e8e8751320
# title: 通常ファイルハンドラ生成
# parent: node-82cb45e7df
# powanKind: organ
# codeLanguage: python

import logging
from pathlib import Path


def create_plain_file_handler(path: str | Path, encoding: str = "utf-8") -> logging.FileHandler:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return logging.FileHandler(path, encoding=encoding)
