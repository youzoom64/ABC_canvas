# powan_id: node-2217838e6d
# title: ロガー取得本体
# parent: node-894cbd722f
# powanKind: organ
# codeLanguage: python

import logging


def get_logger(app_name: str) -> logging.Logger:
    """Return a shared, ready-to-use logger for the given application name.

    This organ owns only the central get_logger flow. Logger-name
    normalization, configured checks, handler preparation, and logger setup
    are delegated to sibling powans under the logger acquisition entry.
    """
    logger_name = normalize_logger_name(app_name)
    logger = logging.getLogger(logger_name)

    if is_logger_configured(logger):
        return logger

    handlers = create_standard_handlers(logger_name)
    apply_logger_config(logger, handlers)
    return logger
