# powan_id: node-e0dbd11130
# title: レベル表示
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

LEVEL_WIDTH = 8


def format_level_name(level_name: str, width: int = LEVEL_WIDTH) -> str:
    return str(level_name or '').upper().ljust(width)[:width]


def level_display_info(level_name: str) -> dict[str, str]:
    name = str(level_name or '').upper()
    colors = {'TRACE':'bright_black','DEBUG':'blue','INFO':'green','WARNING':'yellow','ERROR':'red','CRITICAL':'magenta'}
    return {'name': format_level_name(name), 'color': colors.get(name, 'default')}
