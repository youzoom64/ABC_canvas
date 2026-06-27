# powan_id: node-a22a7f3774
# title: 詳細フォーマッター生成
# parent: node-d8917331df
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging

DETAIL_FORMAT = '%(asctime)s | %(levelname)s | %(process)d | %(threadName)s | %(name)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s'


def create_detail_formatter(datefmt: str | None = '%Y-%m-%d %H:%M:%S') -> logging.Formatter:
    """Create a verbose formatter for troubleshooting."""
    return logging.Formatter(DETAIL_FORMAT, datefmt=datefmt)
