# powan_id: node-3d06feb95b
# title: メッセージ文字列化
# parent: node-b867eee2fd
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def message_to_text(value: object) -> str:
    if value is None:
        return ''
    try:
        return str(value)
    except Exception as exc:
        return f'<unprintable message: {type(exc).__name__}>'
