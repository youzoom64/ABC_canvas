# powan_id: node-c299dfcb1f
# title: 日時形式定義
# parent: node-501b2212e6
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def date_format(value: str | None = None) -> str:
    clean = str(value or '').strip()
    return clean or DEFAULT_DATE_FORMAT
