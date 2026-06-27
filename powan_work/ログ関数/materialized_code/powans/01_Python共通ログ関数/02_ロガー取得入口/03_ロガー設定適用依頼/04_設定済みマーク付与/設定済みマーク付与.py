# powan_id: node-2fb7e9661f
# title: 設定済みマーク付与
# parent: node-4e907d218e
# powanKind: organ
# codeLanguage: python

import logging

DEFAULT_CONFIGURED_ATTR = "_abc_common_logger_configured"


def mark_logger_configured(
    logger: logging.Logger,
    configured_attr: str = DEFAULT_CONFIGURED_ATTR,
) -> logging.Logger:
    """Mark a Logger as already configured and return it."""
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger instance")
    if not isinstance(configured_attr, str) or not configured_attr:
        raise ValueError("configured_attr must be a non-empty string")
    setattr(logger, configured_attr, True)
    return logger


def is_logger_configured(
    logger: logging.Logger,
    configured_attr: str = DEFAULT_CONFIGURED_ATTR,
) -> bool:
    """Return whether a Logger already has the configured marker."""
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger instance")
    if not isinstance(configured_attr, str) or not configured_attr:
        raise ValueError("configured_attr must be a non-empty string")
    return bool(getattr(logger, configured_attr, False))


def mark_configured(logger: logging.Logger) -> logging.Logger:
    """Compatibility wrapper for the parent logger configuration nerve."""
    return mark_logger_configured(logger)


def is_configured(logger: logging.Logger) -> bool:
    """Compatibility wrapper for the parent logger configuration nerve."""
    return is_logger_configured(logger)
