# powan_id: node-76c5714ad9
# title: 例外記録
# parent: node-704b909f82
# powanKind:
# codeLanguage: python

from __future__ import annotations

import logging
import sys
import traceback
from dataclasses import dataclass, fields, replace
from types import TracebackType
from typing import Any, Mapping


@dataclass(frozen=True)
class ExceptionRecordOptions:
    """Options for the exception recording nerve."""

    include_stack: bool = True
    include_chain: bool = True
    include_context: bool = True
    mask_secrets: bool = True
    max_stack_lines: int = 80
    critical_returns_payload: bool = True


SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "credential",
)


def normalize_exception_record_options(options: ExceptionRecordOptions | Mapping[str, Any] | Any | None = None) -> ExceptionRecordOptions:
    """Normalize caller options for exception logging."""
    defaults = ExceptionRecordOptions()
    if options is None:
        return defaults
    if isinstance(options, ExceptionRecordOptions):
        return options

    values: dict[str, Any] = {}
    for field in fields(ExceptionRecordOptions):
        if isinstance(options, Mapping):
            values[field.name] = options.get(field.name, getattr(defaults, field.name))
        else:
            values[field.name] = getattr(options, field.name, getattr(defaults, field.name))

    max_stack_lines = _positive_int(values["max_stack_lines"], default=defaults.max_stack_lines)
    return ExceptionRecordOptions(
        include_stack=bool(values["include_stack"]),
        include_chain=bool(values["include_chain"]),
        include_context=bool(values["include_context"]),
        mask_secrets=bool(values["mask_secrets"]),
        max_stack_lines=max_stack_lines,
        critical_returns_payload=bool(values["critical_returns_payload"]),
    )


def record_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException | tuple[type[BaseException], BaseException, TracebackType] | None = None,
    *,
    level: str = "error",
    context: Mapping[str, Any] | None = None,
    options: ExceptionRecordOptions | Mapping[str, Any] | Any | None = None,
    stack_info: bool = False,
    **log_kwargs: Any,
) -> dict[str, Any]:
    """Record an exception through the shared error/critical nerve.

    This function is the coordination point for exception logging. It extracts
    exception facts, formats traceback text, merges optional context, masks
    sensitive values, emits one logging record, and returns a structured payload
    that tests or higher layers can inspect.
    """
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be an instance of logging.Logger")
    if not isinstance(message, str):
        raise TypeError("message must be a string")

    normalized = normalize_exception_record_options(options)
    exc_type, exc_value, exc_tb = _normalize_exc_info(exc)
    safe_context = _normalize_context(context, mask=normalized.mask_secrets) if normalized.include_context else {}

    exception_info = _extract_exception_info(
        exc_value,
        exc_type=exc_type,
        include_chain=normalized.include_chain,
    )
    stack_text = ""
    if normalized.include_stack and exc_type is not None and exc_value is not None:
        stack_text = _format_exception_trace(exc_type, exc_value, exc_tb, include_chain=normalized.include_chain)
        stack_text = _trim_stack_lines(stack_text, max_lines=normalized.max_stack_lines)

    payload = {
        "level": _normalize_level(level),
        "message": message,
        "exception": exception_info,
        "context": safe_context,
        "traceback": stack_text,
    }
    text = _build_exception_log_message(message, exception_info, stack_text, safe_context)

    emit_kwargs = dict(log_kwargs)
    emit_kwargs.setdefault("extra", {})
    if isinstance(emit_kwargs["extra"], Mapping):
        emit_kwargs["extra"] = dict(emit_kwargs["extra"])
    emit_kwargs["extra"]["exception_record"] = payload
    if stack_info:
        emit_kwargs["stack_info"] = True

    exc_info = (exc_type, exc_value, exc_tb) if exc_type is not None and exc_value is not None else False
    if payload["level"] == "critical":
        logger.critical(text, exc_info=exc_info, **emit_kwargs)
    else:
        logger.error(text, exc_info=exc_info, **emit_kwargs)
    return payload


def record_error_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException | tuple[type[BaseException], BaseException, TracebackType] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Record a handled failure at error level."""
    return record_exception(logger, message, exc, level="error", **kwargs)


def record_critical_exception(
    logger: logging.Logger,
    message: str,
    exc: BaseException | tuple[type[BaseException], BaseException, TracebackType] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Record a dangerous failure at critical level."""
    return record_exception(logger, message, exc, level="critical", **kwargs)


def _normalize_exc_info(
    exc: BaseException | tuple[type[BaseException], BaseException, TracebackType] | None,
) -> tuple[type[BaseException] | None, BaseException | None, TracebackType | None]:
    if exc is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type is None or not isinstance(exc_value, BaseException):
            return None, None, None
        return exc_type, exc_value, exc_tb
    if isinstance(exc, tuple):
        if len(exc) != 3:
            raise ValueError("exc tuple must be a 3-item sys.exc_info() tuple")
        exc_type, exc_value, exc_tb = exc
        if exc_type is not None and not isinstance(exc_value, BaseException):
            raise TypeError("exc tuple value must be a BaseException")
        return exc_type, exc_value, exc_tb
    if isinstance(exc, BaseException):
        return type(exc), exc, exc.__traceback__
    raise TypeError("exc must be an exception, an exc_info tuple, or None")


def _extract_exception_info(
    exc: BaseException | None,
    *,
    exc_type: type[BaseException] | None = None,
    include_chain: bool = True,
) -> dict[str, Any]:
    if exc is None:
        return {"type": None, "module": None, "qualified_type": None, "message": None, "chain": []}
    cls = exc_type or type(exc)
    info: dict[str, Any] = {
        "type": cls.__name__,
        "module": cls.__module__,
        "qualified_type": f"{cls.__module__}.{cls.__qualname__}",
        "message": _safe_str(exc),
    }
    if include_chain:
        info["chain"] = _extract_exception_chain(exc)
    return info


def _extract_exception_chain(exc: BaseException, *, limit: int = 20) -> list[dict[str, str]]:
    chain: list[dict[str, str]] = []
    seen: set[int] = set()
    current = exc.__cause__ or exc.__context__
    while current is not None and id(current) not in seen and len(chain) < limit:
        seen.add(id(current))
        chain.append({
            "type": type(current).__name__,
            "qualified_type": f"{type(current).__module__}.{type(current).__qualname__}",
            "message": _safe_str(current),
        })
        current = current.__cause__ or current.__context__
    return chain


def _format_exception_trace(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
    *,
    include_chain: bool,
) -> str:
    return "".join(traceback.format_exception(exc_type, exc, tb, chain=include_chain)).rstrip()


def _build_exception_log_message(
    message: str,
    exception_info: Mapping[str, Any],
    stack: str,
    context: Mapping[str, Any],
) -> str:
    parts = [message.rstrip() or "Exception captured"]
    if exception_info.get("type"):
        parts.append(f"Exception: {exception_info.get('qualified_type')}: {exception_info.get('message')}")
    if context:
        parts.append("Context: " + ", ".join(f"{key}={value!r}" for key, value in sorted(context.items())))
    if stack:
        parts.append("Traceback:\n" + stack)
    return "\n".join(parts)


def _normalize_context(context: Mapping[str, Any] | None, *, mask: bool) -> dict[str, Any]:
    if not context:
        return {}
    normalized: dict[str, Any] = {}
    for key, value in context.items():
        text_key = str(key)
        normalized[text_key] = "***" if mask and _is_sensitive_key(text_key) else _safe_context_value(value)
    return normalized


def _is_sensitive_key(key: str) -> bool:
    text = key.lower().replace("-", "_")
    return any(part in text for part in SENSITIVE_KEY_PARTS)


def _safe_context_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    try:
        return repr(value)
    except Exception as repr_error:
        return f"<unrepresentable {type(value).__name__}: {repr_error}>"


def _trim_stack_lines(text: str, *, max_lines: int) -> str:
    lines = text.splitlines()
    if max_lines <= 0 or len(lines) <= max_lines:
        return text
    head = max(1, max_lines // 2)
    tail = max(1, max_lines - head - 1)
    omitted = len(lines) - head - tail
    return "\n".join([*lines[:head], f"... omitted {omitted} stack lines ...", *lines[-tail:]])


def _normalize_level(level: str) -> str:
    normalized = str(level or "error").strip().lower()
    if normalized not in {"error", "critical"}:
        raise ValueError("exception records support only error or critical level")
    return normalized


def _positive_int(value: Any, *, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _safe_str(value: Any) -> str:
    try:
        return str(value)
    except Exception as stringify_error:
        return f"<failed to stringify {type(value).__name__}: {stringify_error}>"
