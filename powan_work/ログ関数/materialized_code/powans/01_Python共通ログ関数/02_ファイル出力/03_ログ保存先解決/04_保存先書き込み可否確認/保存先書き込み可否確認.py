# powan_id: node-f3f670a073
# title: 保存先書き込み可否確認
# parent: node-ea984eb4ea
# powanKind: organ
# codeLanguage: python

from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def can_write_log_directory(path: PathLike) -> bool:
    directory = Path(path)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".abc_log_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False
