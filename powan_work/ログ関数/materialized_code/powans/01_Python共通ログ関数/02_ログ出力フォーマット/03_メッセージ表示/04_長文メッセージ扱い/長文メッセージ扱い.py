# powan_id: node-968814aba2
# title: 長文メッセージ扱い
# parent: node-b867eee2fd
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def limit_message_length(message: str, max_length: int | None = None, suffix: str = '...') -> str:
    """Return message shortened to max_length without breaking log formatting."""
    try:
        text = str(message)
    except Exception as exc:
        text = f'<unprintable message: {type(exc).__name__}>'

    if max_length is None or max_length < 0 or len(text) <= max_length:
        return text
    if max_length <= 0:
        return ''

    try:
        marker = str(suffix)
    except Exception:
        marker = '...'

    if len(marker) >= max_length:
        return marker[:max_length]

    return text[: max_length - len(marker)] + marker
