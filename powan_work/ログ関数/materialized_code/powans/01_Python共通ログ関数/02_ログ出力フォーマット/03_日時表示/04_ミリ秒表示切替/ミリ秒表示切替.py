# powan_id: node-9753a00fd4
# title: ミリ秒表示切替
# parent: node-501b2212e6
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def date_format_with_milliseconds(enabled: bool, base_format: str = '%Y-%m-%d %H:%M:%S') -> str:
    return f'{base_format}.%f' if enabled and '%f' not in base_format else base_format


def trim_to_milliseconds(text: str) -> str:
    return text[:-3] if '.' in text and len(text.rsplit('.', 1)[-1]) == 6 else text
