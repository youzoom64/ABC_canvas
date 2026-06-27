# powan_id: node-2d5e0ca221
# title: 通常フォーマッター生成
# parent: node-d8917331df
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging

NORMAL_FORMAT = '%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s'


def create_normal_formatter(datefmt: str | None = '%Y-%m-%d %H:%M:%S') -> logging.Formatter:
    """Create a readable formatter for normal application logs."""
    return logging.Formatter(NORMAL_FORMAT, datefmt=datefmt)
