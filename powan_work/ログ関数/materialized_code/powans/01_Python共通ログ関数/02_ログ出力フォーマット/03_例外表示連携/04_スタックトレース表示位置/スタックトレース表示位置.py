# powan_id: node-4b17d2bc39
# title: スタックトレース表示位置
# parent: node-3341b41223
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Literal

TracebackPosition = Literal['after_message', 'new_block']
VALID_POSITIONS: set[str] = {'after_message', 'new_block'}


def normalize_traceback_position(value: str | None = None) -> TracebackPosition:
    """Normalize where traceback text should be placed in a formatted log."""
    text = str(value or 'after_message').strip().lower()
    if text not in VALID_POSITIONS:
        raise ValueError(f'unknown traceback position: {value!r}')
    return text  # type: ignore[return-value]
