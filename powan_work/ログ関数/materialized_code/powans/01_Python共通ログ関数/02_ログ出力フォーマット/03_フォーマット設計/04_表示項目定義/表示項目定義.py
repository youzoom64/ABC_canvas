# powan_id: node-0aa4fec7b9
# title: 表示項目定義
# parent: node-bca7963924
# powanKind: organ
# codeLanguage: python

"""Display field definition organ for log formatting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogFieldSpec:
    key: str
    label: str
    required: bool = True
    default: str = "-"


def define_display_fields() -> tuple[LogFieldSpec, ...]:
    """Return the canonical fields included in a human-readable log line."""

    return (
        LogFieldSpec("timestamp", "日時"),
        LogFieldSpec("level", "ログレベル"),
        LogFieldSpec("app", "アプリ名"),
        LogFieldSpec("module", "モジュール名"),
        LogFieldSpec("line", "行番号", required=False),
        LogFieldSpec("message", "メッセージ"),
    )
