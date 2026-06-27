# powan_id: node-97d5f415e0
# title: レベル名整形
# parent: node-e0dbd11130
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def normalize_level_label(level_name: str) -> str:
    return str(level_name or '').strip().upper()
