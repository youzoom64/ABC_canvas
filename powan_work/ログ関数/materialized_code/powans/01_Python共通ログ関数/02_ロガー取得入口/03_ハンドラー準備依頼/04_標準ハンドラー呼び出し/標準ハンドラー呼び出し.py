# powan_id: node-f482afaa80
# title: 標準ハンドラー呼び出し
# parent: node-e4916a59ac
# powanKind: organ
# codeLanguage: python

import logging
from typing import Optional, TextIO, Tuple


def create_standard_handlers(
    app_name: str,
    *,
    file_path: Optional[str] = None,
    level: int = logging.INFO,
    stream: Optional[TextIO] = None,
    encoding: str = "utf-8",
) -> Tuple[logging.Handler, ...]:
    """Create the standard handlers for an application logger.

    Always creates a stream handler, and adds a file handler only when
    file_path is provided. Formatting and external configuration are left to
    the caller or surrounding powans.
    """
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setLevel(level)

    handlers: list[logging.Handler] = [stream_handler]

    if file_path is not None:
        file_handler = logging.FileHandler(file_path, encoding=encoding)
        file_handler.setLevel(level)
        handlers.append(file_handler)

    return tuple(handlers)
