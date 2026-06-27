# powan_id: node-d13bbaf356
# title: 拡張子補完
# parent: node-6633b95abc
# powanKind: organ
# codeLanguage: python

from pathlib import Path


def ensure_log_suffix(filename: str, suffix: str = ".log") -> str:
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    path = Path(filename)
    return str(path if path.suffix else path.with_suffix(suffix))
