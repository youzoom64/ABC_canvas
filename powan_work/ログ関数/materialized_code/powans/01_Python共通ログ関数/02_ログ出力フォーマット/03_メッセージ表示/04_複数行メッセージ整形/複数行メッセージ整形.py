# powan_id: node-2a6d63e5cb
# title: 複数行メッセージ整形
# parent: node-b867eee2fd
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def format_multiline_message(message: str, indent: str = '    ') -> str:
    """Indent continuation lines so multi-line log messages stay readable."""
    try:
        text = str(message)
    except Exception as exc:
        text = f'<unprintable message: {type(exc).__name__}>'

    lines = text.splitlines()
    if len(lines) <= 1:
        return text
    return lines[0] + '\n' + '\n'.join(indent + line for line in lines[1:])
