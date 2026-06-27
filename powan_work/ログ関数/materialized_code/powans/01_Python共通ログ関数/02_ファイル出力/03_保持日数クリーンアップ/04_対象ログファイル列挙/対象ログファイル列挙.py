# powan_id: node-e8666a0ea5
# title: 対象ログファイル列挙
# parent: node-ce9e2eeef0
# powanKind: organ
# codeLanguage: python

from pathlib import Path


def list_log_files(directory: str | Path, pattern: str = "*.log") -> list[Path]:
    base = Path(directory)
    if not base.exists():
        return []
    return sorted(path for path in base.glob(pattern) if path.is_file())
