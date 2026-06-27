# powan_id: node-c2b12a778c
# title: 保存先ディレクトリ作成
# parent: node-ea984eb4ea
# powanKind: organ
# codeLanguage: python

from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def create_log_directory(path: PathLike) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
