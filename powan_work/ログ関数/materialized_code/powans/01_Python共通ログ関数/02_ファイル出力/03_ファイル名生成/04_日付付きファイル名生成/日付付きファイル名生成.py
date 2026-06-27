# powan_id: node-25279f4cee
# title: 日付付きファイル名生成
# parent: node-6633b95abc
# powanKind: organ
# codeLanguage: python

from datetime import date
from typing import Optional


def make_dated_log_filename(stem: str, day: Optional[date] = None, suffix: str = ".log") -> str:
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return f"{stem}_{day or date.today():%Y%m%d}{suffix}"
