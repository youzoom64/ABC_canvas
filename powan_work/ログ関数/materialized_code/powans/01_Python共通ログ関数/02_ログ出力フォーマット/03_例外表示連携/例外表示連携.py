# powan_id: node-3341b41223
# title: 例外表示連携
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Literal

TracebackPosition = Literal['after_message', 'new_block']
VALID_TRACEBACK_POSITIONS: set[str] = {'after_message', 'new_block'}


def has_exception(record: logging.LogRecord) -> bool:
    """Return True when a log record carries exception details."""
    return bool(getattr(record, 'exc_info', None) or getattr(record, 'exc_text', None))


def exception_position(value: str | None = None) -> TracebackPosition:
    """Normalize where traceback text should appear in formatted logs."""
    text = str(value or 'after_message').strip().lower()
    if text not in VALID_TRACEBACK_POSITIONS:
        raise ValueError(f'unknown traceback position: {value!r}')
    return text  # type: ignore[return-value]


def should_append_exception(record: logging.LogRecord) -> bool:
    """Tell the formatter whether exception text should be attached."""
    return has_exception(record)


def exception_display_plan(record: logging.LogRecord, position: str | None = None) -> dict[str, object]:
    """Return the formatter-facing exception display decision."""
    return {
        'hasException': has_exception(record),
        'tracebackPosition': exception_position(position),
    }
