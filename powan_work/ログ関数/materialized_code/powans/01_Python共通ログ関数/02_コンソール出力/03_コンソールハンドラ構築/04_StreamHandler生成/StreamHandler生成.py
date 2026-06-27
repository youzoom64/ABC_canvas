# powan_id: node-c44e5be3ea
# title: StreamHandler生成
# parent: node-37cb41da55
# powanKind: organ
# codeLanguage: python

"""Create a standard logging StreamHandler for console output."""

from __future__ import annotations

import logging
import sys
from typing import TextIO


def create_stream_handler(stream: TextIO | None = None) -> logging.StreamHandler:
    """Return a StreamHandler aimed at the requested console stream.

    ``sys.stderr`` is the default because Python's standard logging console
    handler uses stderr unless a stream is supplied explicitly.
    """
    return logging.StreamHandler(stream if stream is not None else sys.stderr)


__all__ = ["create_stream_handler"]
