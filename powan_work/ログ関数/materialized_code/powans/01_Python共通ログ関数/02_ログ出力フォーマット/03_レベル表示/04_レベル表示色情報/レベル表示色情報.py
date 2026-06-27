# powan_id: node-3b200bcae8
# title: レベル表示色情報
# parent: node-e0dbd11130
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

LEVEL_COLORS = {'TRACE':'bright_black','DEBUG':'blue','INFO':'green','WARNING':'yellow','ERROR':'red','CRITICAL':'magenta'}


def color_for_level(level_name: str) -> str:
    return LEVEL_COLORS.get(str(level_name or '').upper(), 'default')
