# powan_id: node-e6baf7a40c
# title: ローテーション設定
# parent: node-92b7df4887
# powanKind: nerve
# codeLanguage: python

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RotationConfig:
    mode: str = "none"
    max_bytes: int = 0
    backup_count: int = 7
    when: str = "midnight"
    interval: int = 1


def parse_rotation_config(config: Mapping[str, Any] | None = None) -> RotationConfig:
    data = dict(config or {})
    return RotationConfig(
        mode=str(data.get("mode") or data.get("rotation") or "none").lower(),
        max_bytes=max(0, int(data.get("max_bytes") or data.get("maxBytes") or 0)),
        backup_count=max(0, int(data.get("backup_count") or data.get("backupCount") or 7)),
        when=str(data.get("when") or "midnight"),
        interval=max(1, int(data.get("interval") or 1)),
    )
