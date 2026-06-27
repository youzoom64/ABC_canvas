# powan_id: node-96c74fd70f
# title: 古いログ削除
# parent: node-ce9e2eeef0
# powanKind: organ
# codeLanguage: python

from pathlib import Path


def delete_old_log(path: str | Path, missing_ok: bool = True) -> bool:
    target = Path(path)
    if not target.exists():
        if missing_ok:
            return False
        raise FileNotFoundError(target)
    if not target.is_file():
        raise IsADirectoryError(target)
    target.unlink()
    return True
