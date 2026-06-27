# powan_id: node-228dc030f3
# title: フォーマット文字列生成
# parent: node-d8917331df
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def build_format_string(fields: list[str] | tuple[str, ...], separator: str = ' | ') -> str:
    """Build a logging format string from logging record field names."""
    if not fields:
        raise ValueError('at least one logging field is required')
    return separator.join(f'%({field})s' for field in fields)
