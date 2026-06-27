# powan_id: node-d8917331df
# title: logging Formatter生成
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Literal

SIMPLE_FORMAT = '%(levelname)s | %(message)s'
NORMAL_FORMAT = '%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s'
DETAIL_FORMAT = '%(asctime)s | %(levelname)s | %(process)d | %(threadName)s | %(name)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s'

FormatterStyle = Literal['simple', 'normal', 'detail']

_FORMATS: dict[str, str] = {
    'simple': SIMPLE_FORMAT,
    'normal': NORMAL_FORMAT,
    'detail': DETAIL_FORMAT,
}


def create_formatter(
    style: FormatterStyle | str = 'normal',
    datefmt: str | None = '%Y-%m-%d %H:%M:%S',
) -> logging.Formatter:
    """Create a standard logging.Formatter for the requested use case."""
    return logging.Formatter(get_format_string(style), datefmt=datefmt)


def create_simple_formatter() -> logging.Formatter:
    """Create a compact formatter for short console output."""
    return logging.Formatter(SIMPLE_FORMAT)


def create_normal_formatter(datefmt: str | None = '%Y-%m-%d %H:%M:%S') -> logging.Formatter:
    """Create a readable formatter for normal application logs."""
    return logging.Formatter(NORMAL_FORMAT, datefmt=datefmt)


def create_detail_formatter(datefmt: str | None = '%Y-%m-%d %H:%M:%S') -> logging.Formatter:
    """Create a verbose formatter for troubleshooting."""
    return logging.Formatter(DETAIL_FORMAT, datefmt=datefmt)


def get_format_string(style: FormatterStyle | str = 'normal') -> str:
    """Return the format string behind a formatter style."""
    return _FORMATS.get(style, NORMAL_FORMAT)


def build_format_string(fields: list[str] | tuple[str, ...], separator: str = ' | ') -> str:
    """Build a logging format string from logging record field names."""
    if not fields:
        raise ValueError('at least one logging field is required')
    return separator.join(f'%({field})s' for field in fields)
