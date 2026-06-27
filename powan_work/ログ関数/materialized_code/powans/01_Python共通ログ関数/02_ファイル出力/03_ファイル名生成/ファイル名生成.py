# powan_id: node-6633b95abc
# title: ファイル名生成
# parent: node-92b7df4887
# powanKind: nerve
# codeLanguage: python

from datetime import date
from pathlib import Path
import re
from typing import Optional

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_log_stem(app_name: Optional[str], default: str = "app") -> str:
    stem = _SAFE.sub("_", (app_name or default).strip()).strip("._-")
    return stem or default


def make_log_filename(app_name: Optional[str], *, dated: bool = False, suffix: str = ".log") -> str:
    stem = safe_log_stem(app_name)
    if dated:
        stem = f"{stem}_{date.today():%Y%m%d}"
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return str(Path(stem).with_suffix(suffix))
