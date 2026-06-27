# powan_id: node-7c6181f749
# title: 簡易フォーマッター生成
# parent: node-d8917331df
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging

SIMPLE_FORMAT = '%(levelname)s | %(message)s'


def create_simple_formatter() -> logging.Formatter:
    """Create a compact formatter for short console output."""
    return logging.Formatter(SIMPLE_FORMAT)
