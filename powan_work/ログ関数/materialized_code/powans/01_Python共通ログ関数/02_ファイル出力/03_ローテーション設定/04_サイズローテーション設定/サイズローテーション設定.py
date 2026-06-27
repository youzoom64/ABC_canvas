# powan_id: node-2c20839316
# title: サイズローテーション設定
# parent: node-e6baf7a40c
# powanKind: organ
# codeLanguage: python

from dataclasses import dataclass


@dataclass(frozen=True)
class SizeRotation:
    max_bytes: int
    backup_count: int = 7


def make_size_rotation(max_bytes: int = 10 * 1024 * 1024, backup_count: int = 7) -> SizeRotation:
    return SizeRotation(max_bytes=max(1, int(max_bytes)), backup_count=max(0, int(backup_count)))
