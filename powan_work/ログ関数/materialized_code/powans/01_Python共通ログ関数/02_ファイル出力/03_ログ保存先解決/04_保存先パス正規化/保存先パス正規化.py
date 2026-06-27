# powan_id: node-3d73eba843
# title: 保存先パス正規化
# parent: node-ea984eb4ea
# powanKind: organ
# codeLanguage: python

from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]


def normalize_log_path(path: Optional[PathLike], default: PathLike = "logs") -> Path:
    chosen = default if path in (None, "") else path
    resolved = Path(chosen).expanduser()
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved
    return resolved.resolve()
