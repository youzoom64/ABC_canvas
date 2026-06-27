# powan_id: node-7c738b2f00
# title: アプリ名ファイル名化
# parent: node-6633b95abc
# powanKind: organ
# codeLanguage: python

import re
from typing import Optional

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def app_name_to_file_stem(app_name: Optional[str], default: str = "app") -> str:
    stem = _SAFE.sub("_", (app_name or default).strip()).strip("._-")
    return stem or default
