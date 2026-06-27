# powan_id: node-95a6fc98d8
# title: 例外付きログ判定
# parent: node-3341b41223
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging


def record_has_exception(record: logging.LogRecord) -> bool:
    """Return True when a log record includes exception information."""
    return bool(getattr(record, 'exc_info', None) or getattr(record, 'exc_text', None))
