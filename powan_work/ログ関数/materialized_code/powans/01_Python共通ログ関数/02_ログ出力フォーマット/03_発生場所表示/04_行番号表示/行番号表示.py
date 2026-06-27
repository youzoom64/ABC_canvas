# powan_id: node-269bc71eec
# title: 行番号表示
# parent: node-0b0c56f7ad
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def display_line_number(lineno: int | str | None) -> str:
    if lineno in (None, ''):
        return '?'
    value = int(lineno)
    return str(value) if value >= 0 else '?'
