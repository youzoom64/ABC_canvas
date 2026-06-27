# powan_id: node-6178896ba5
# title: レベル適用
# parent: node-4e907d218e
# powanKind: organ
# codeLanguage: python

import logging
from collections.abc import Iterable


def apply_level(
    logger: logging.Logger,
    handlers: logging.Handler | Iterable[logging.Handler],
    level: int = logging.INFO,
) -> logging.Logger:
    """Apply a standard logging level to the logger and handler input."""
    logger.setLevel(level)
    if isinstance(handlers, logging.Handler):
        handlers.setLevel(level)
        return logger
    for handler in handlers:
        handler.setLevel(level)
    return logger
