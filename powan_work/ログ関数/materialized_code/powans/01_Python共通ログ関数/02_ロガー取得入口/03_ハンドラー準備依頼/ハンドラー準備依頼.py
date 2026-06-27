# powan_id: node-e4916a59ac
# title: ハンドラー準備依頼
# parent: node-894cbd722f
# powanKind: nerve
# codeLanguage: python

import logging
from typing import Optional, TextIO, Tuple


def prepare_logger_handlers(
    app_name: str,
    *,
    file_path: Optional[str] = None,
    level: int = logging.INFO,
    stream: Optional[TextIO] = None,
    encoding: str = "utf-8",
) -> Tuple[logging.Handler, ...]:
    """Prepare the handlers required by get_logger.

    This nerve powan only connects the child operations: it asks the
    standard-handler child to create handlers from the provided arguments,
    then asks the normalization child to return them as a tuple.
    """
    handlers = create_standard_handlers(
        app_name,
        file_path=file_path,
        level=level,
        stream=stream,
        encoding=encoding,
    )
    return normalize_handlers(handlers)
