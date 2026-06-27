# powan_id: node-8af9787df1
# title: loggingメソッド拡張
# parent: node-8a2f4ee457
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Any, Callable, Final, Optional, cast


DEFAULT_TRACE_LEVEL: Final[int] = 5
TRACE_METHOD_NAME: Final[str] = "trace"


def _resolve_trace_level() -> int:
    """Return the TRACE level registered by the logging bridge, or its default."""
    return int(getattr(logging, "TRACE", DEFAULT_TRACE_LEVEL))


def logger_trace(self: logging.Logger, message: object, *args: object, **kwargs: Any) -> None:
    """Write a TRACE log record through ``logging.Logger``.

    This method is meant to be installed as ``logging.Logger.trace``. It only
    creates the call entry point; TRACE registration belongs to the sibling
    powan that owns level registration.
    """
    trace_level = _resolve_trace_level()
    if self.isEnabledFor(trace_level):
        self._log(trace_level, message, args, **kwargs)


def install_logger_trace_method(
    *,
    method_name: str = TRACE_METHOD_NAME,
    method: Optional[Callable[..., None]] = None,
    overwrite: bool = False,
) -> Callable[..., None]:
    """Install ``logger.trace(...)`` on ``logging.Logger``.

    The install is idempotent by default, so calling this more than once keeps
    an existing method in place unless ``overwrite=True`` is requested.
    """
    if not method_name.isidentifier():
        raise ValueError(f"method_name must be a valid Python identifier: {method_name!r}")

    existing = getattr(logging.Logger, method_name, None)
    if existing is not None and not overwrite:
        return cast(Callable[..., None], existing)

    installed = method if method is not None else logger_trace
    setattr(logging.Logger, method_name, installed)
    return installed


__all__ = [
    "DEFAULT_TRACE_LEVEL",
    "TRACE_METHOD_NAME",
    "install_logger_trace_method",
    "logger_trace",
]
