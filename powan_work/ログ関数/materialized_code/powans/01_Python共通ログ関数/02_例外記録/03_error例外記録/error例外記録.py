# powan_id: node-d68d98e101
# title: error例外記録
# parent: node-76c5714ad9
# powanKind: organ
# codeLanguage: python

import logging
import sys
from types import TracebackType
from typing import Any, Mapping


def log_error_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException | tuple[type[BaseException], BaseException, TracebackType] | None = None,
    *,
    extra: Mapping[str, Any] | None = None,
    stack_info: bool = False,
    **kwargs: Any,
) -> None:
    """Log a normal handled failure at error level with exception details.

    This function is a small shared logging entry point for failures that are
    expected to be handled by the caller but still need enough information for
    later diagnosis. It preserves exception information for traceback output and
    avoids mutating the caller's extra mapping.
    """
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be an instance of logging.Logger")
    if not isinstance(message, str):
        raise TypeError("message must be a string")

    exc_info: bool | tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None]
    if exc is None:
        current_exc = sys.exc_info()
        exc_info = current_exc if current_exc[0] is not None else False
    elif isinstance(exc, tuple):
        if len(exc) != 3:
            raise ValueError("exc tuple must be a 3-item sys.exc_info() tuple")
        exc_info = exc
    elif isinstance(exc, BaseException):
        exc_info = (type(exc), exc, exc.__traceback__)
    else:
        raise TypeError("exc must be an exception, an exc_info tuple, or None")

    log_kwargs = dict(kwargs)
    if extra is not None:
        log_kwargs["extra"] = dict(extra)
    if stack_info:
        log_kwargs["stack_info"] = True

    logger.error(message, exc_info=exc_info, **log_kwargs)
