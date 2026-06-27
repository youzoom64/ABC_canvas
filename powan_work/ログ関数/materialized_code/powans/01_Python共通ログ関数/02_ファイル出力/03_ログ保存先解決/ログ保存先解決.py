# powan_id: node-ea984eb4ea
# title: ログ保存先解決
# parent: node-92b7df4887
# powanKind: nerve
# codeLanguage: python

from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def resolve_log_directory(base_dir: PathLike = "logs", create: bool = True) -> Path:
    path = Path(base_dir).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_log_directory_writable(base_dir: PathLike = "logs") -> Path:
    path = resolve_log_directory(base_dir, create=True)
    probe = path / ".write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
    finally:
        if probe.exists():
            probe.unlink()
    return path
