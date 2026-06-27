# powan_id: node-f3e852186d
# title: メッセージ安全整形
# parent: node-bbc4e005cb
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import traceback
import unicodedata

_LINE_BREAK_MARK = " \u23ce "
_CONTROL_REPLACEMENTS = {
    "\t": " ",
    "\n": _LINE_BREAK_MARK,
    "\r": _LINE_BREAK_MARK,
}


def sanitize_console_message(
    message: Any,
    *,
    none_text: str = "",
    include_exception_type: bool = True,
    include_traceback: bool = False,
    max_length: int | None = 4000,
    replacement: str = "?",
) -> str:
    """Return a console-safe, single-line representation of a log message.

    The result avoids raw newlines and most control characters so a message can be
    printed inside one console log record without breaking the surrounding layout.
    """
    text = _message_to_text(
        message,
        none_text=none_text,
        include_exception_type=include_exception_type,
        include_traceback=include_traceback,
    )
    text = _normalize_line_breaks(text)
    text = _replace_control_characters(text, replacement=replacement)
    text = _collapse_soft_spacing(text)

    if max_length is not None and max_length >= 0 and len(text) > max_length:
        omitted = len(text) - max_length
        suffix = f" ...[truncated {omitted} chars]"
        keep = max(0, max_length - len(suffix))
        text = text[:keep].rstrip() + suffix

    return text


def _message_to_text(
    message: Any,
    *,
    none_text: str,
    include_exception_type: bool,
    include_traceback: bool,
) -> str:
    if message is None:
        return none_text

    if isinstance(message, BaseException):
        if include_traceback and message.__traceback__ is not None:
            return "".join(
                traceback.format_exception(type(message), message, message.__traceback__)
            )
        if include_exception_type:
            return f"{type(message).__name__}: {message}"
        return str(message)

    try:
        return str(message)
    except Exception as exc:  # pragma: no cover - defensive fallback for hostile __str__.
        return f"<unprintable {type(message).__name__}: {type(exc).__name__}: {exc}>"


def _normalize_line_breaks(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return _LINE_BREAK_MARK.join(part.strip() for part in text.split("\n"))


def _replace_control_characters(text: str, *, replacement: str) -> str:
    safe_chars: list[str] = []
    for char in text:
        if char in _CONTROL_REPLACEMENTS:
            safe_chars.append(_CONTROL_REPLACEMENTS[char])
            continue
        category = unicodedata.category(char)
        if category.startswith("C") and category not in {"Co"}:
            safe_chars.append(replacement)
            continue
        safe_chars.append(char)
    return "".join(safe_chars)


def _collapse_soft_spacing(text: str) -> str:
    parts = text.split(" ")
    collapsed: list[str] = []
    previous_empty = False
    for part in parts:
        if part == "":
            if not previous_empty:
                collapsed.append(part)
            previous_empty = True
            continue
        collapsed.append(part)
        previous_empty = False
    return " ".join(collapsed).strip()


def sanitize_console_messages(messages: Iterable[Any], **kwargs: Any) -> list[str]:
    """Sanitize several messages with the same options."""
    return [sanitize_console_message(message, **kwargs) for message in messages]


def default_message_sanitizer(message: Any) -> str:
    """Compatibility wrapper used by the parent console formatter."""
    return sanitize_console_message(message)


__all__ = [
    "sanitize_console_message",
    "sanitize_console_messages",
    "default_message_sanitizer",
]
