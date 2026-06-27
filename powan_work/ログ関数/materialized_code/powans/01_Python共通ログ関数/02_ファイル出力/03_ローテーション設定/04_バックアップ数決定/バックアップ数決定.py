# powan_id: node-579fe8f43b
# title: バックアップ数決定
# parent: node-e6baf7a40c
# powanKind: organ
# codeLanguage: python

from typing import Any, Mapping


def decide_backup_count(config: Mapping[str, Any] | None = None, default: int = 7) -> int:
    data = config or {}
    value = data.get("backup_count", data.get("backupCount", default))
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return max(0, int(default))
