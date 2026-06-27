# powan_id: node-5bb45a9fb3
# title: critical例外記録
# parent: node-76c5714ad9
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import Mapping
from typing import Any


def log_critical_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException | None = None,
    /,
    **context: Any,
) -> dict[str, Any]:
    """Record a dangerous exception at critical level with traceback and context.

    The function does not configure logging, open files, terminate the process,
    or re-raise the exception. It only emits one critical log record and returns
    the normalized payload so shared application logging layers can test or
    forward the same details.
    """

    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger instance")
    if not message:
        message = "Critical exception captured"

    active_exc = exc
    if active_exc is None:
        current_type, current_exc, _ = sys.exc_info()
        if current_type is not None and isinstance(current_exc, BaseException):
            active_exc = current_exc

    normalized_context = _safe_context(context)
    payload: dict[str, Any] = {
        "message": str(message),
        "severity": "critical",
        "context": normalized_context,
        "exception_type": None,
        "exception_message": None,
        "traceback": None,
    }

    exc_info: tuple[type[BaseException], BaseException, Any] | bool
    exc_info = False
    if active_exc is not None:
        exc_type = type(active_exc)
        tb = active_exc.__traceback__
        exc_info = (exc_type, active_exc, tb)
        payload["exception_type"] = f"{exc_type.__module__}.{exc_type.__qualname__}"
        payload["exception_message"] = str(active_exc)
        payload["traceback"] = "".join(traceback.format_exception(exc_type, active_exc, tb))

    logger.critical(
        "%s",
        payload["message"],
        exc_info=exc_info,
        extra={"critical_exception": payload},
    )
    return payload


def _safe_context(context: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in context.items():
        text_key = str(key)
        try:
            repr(value)
        except Exception as repr_error:  # pragma: no cover - defensive against hostile objects
            safe[text_key] = f"<unrepresentable {type(value).__name__}: {repr_error}>"
        else:
            safe[text_key] = value
    return safe
