# powan_id: node-ce9e2eeef0
# title: 保持日数クリーンアップ
# parent: node-92b7df4887
# powanKind: nerve
# codeLanguage: python

from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_logs(directory: str | Path, *, days: int, pattern: str = "*.log") -> list[Path]:
    cutoff = datetime.now().timestamp() - timedelta(days=max(0, days)).total_seconds()
    removed: list[Path] = []
    for path in Path(directory).glob(pattern):
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path)
    return removed
