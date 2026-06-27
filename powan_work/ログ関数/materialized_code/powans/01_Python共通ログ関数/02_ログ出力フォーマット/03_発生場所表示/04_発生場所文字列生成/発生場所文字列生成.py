# powan_id: node-784e538d05
# title: 発生場所文字列生成
# parent: node-0b0c56f7ad
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def location_text(module: str | None, func: str | None, lineno: int | str | None) -> str:
    module_text = str(module or '<module>').strip() or '<module>'
    func_text = str(func or '').strip()
    line_text = '?' if lineno in (None, '') else str(lineno)
    name = f'{module_text}.{func_text}' if func_text else module_text
    return f'{name}:{line_text}'
