# powan_id: node-3e2dc15654
# title: 期限切れログ判定
# parent: node-ce9e2eeef0
# powanKind: organ
# codeLanguage: python

from datetime import datetime, timedelta
from pathlib import Path


def is_expired_log(path: str | Path, *, days: int, now: datetime | None = None) -> bool:
    current = now or datetime.now()
    cutoff = current - timedelta(days=max(0, days))
    return datetime.fromtimestamp(Path(path).stat().st_mtime) < cutoff
