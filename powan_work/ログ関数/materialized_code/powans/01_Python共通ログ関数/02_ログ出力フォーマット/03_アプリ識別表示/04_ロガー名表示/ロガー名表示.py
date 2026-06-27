# powan_id: node-146cf3e1f7
# title: ロガー名表示
# parent: node-90c2d94129
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def display_logger_name(logger_name: str | None, max_parts: int | None = None) -> str:
    parts = [part for part in str(logger_name or '').split('.') if part]
    if not parts:
        return 'root'
    if max_parts and max_parts > 0:
        parts = parts[-max_parts:]
    return '.'.join(parts)
