# powan_id: node-501b2212e6
# title: 日時表示
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
MILLISECOND_DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


def logging_date_format(include_milliseconds: bool = False) -> str:
    return MILLISECOND_DATE_FORMAT if include_milliseconds else DEFAULT_DATE_FORMAT


def trim_microseconds(text: str, include_milliseconds: bool = False) -> str:
    return text[:-3] if include_milliseconds and '.' in text else text
