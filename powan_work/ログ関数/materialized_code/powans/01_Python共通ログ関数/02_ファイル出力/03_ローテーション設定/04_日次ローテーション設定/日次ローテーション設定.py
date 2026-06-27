# powan_id: node-238808ee83
# title: 日次ローテーション設定
# parent: node-e6baf7a40c
# powanKind: organ
# codeLanguage: python

from dataclasses import dataclass


@dataclass(frozen=True)
class TimedRotation:
    when: str = "midnight"
    interval: int = 1
    backup_count: int = 7
    utc: bool = False


def make_daily_rotation(backup_count: int = 7, utc: bool = False) -> TimedRotation:
    return TimedRotation(backup_count=max(0, int(backup_count)), utc=bool(utc))
