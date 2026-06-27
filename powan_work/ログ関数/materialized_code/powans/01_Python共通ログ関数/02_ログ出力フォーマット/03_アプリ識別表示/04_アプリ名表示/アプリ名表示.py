# powan_id: node-174ce786ae
# title: アプリ名表示
# parent: node-90c2d94129
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def display_app_name(app_name: str | None, fallback: str = 'app') -> str:
    return str(app_name or '').strip() or fallback
