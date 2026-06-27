# powan_id: node-d6fb1590bd
# title: propagate制御
# parent: node-4e907d218e
# powanKind: organ
# codeLanguage: python

import logging


def set_logger_propagate(
    logger: logging.Logger,
    propagate: bool = False,
) -> logging.Logger:
    """Set logger propagation after validating the logger instance."""
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger instance")
    logger.propagate = bool(propagate)
    return logger


def control_propagate(
    logger: logging.Logger,
    propagate: bool = False,
) -> logging.Logger:
    """Compatibility wrapper for the parent logger configuration flow."""
    return set_logger_propagate(logger, propagate)
