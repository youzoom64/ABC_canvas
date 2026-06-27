# powan_id: node-0b0c56f7ad
# title: 発生場所表示
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

"""発生場所表示ポワン: モジュール名・関数名・行番号の表示を束ねる窓口。"""
from __future__ import annotations

from dataclasses import dataclass
from types import FrameType
from typing import Any, Mapping


@dataclass(frozen=True)
class SourceLocation:
    """ログ発生元を、人が追いやすい最小情報で保持する値。"""

    module: str
    function: str
    line: int | None


def format_module_name(record: Any) -> str:
    """LogRecord風オブジェクトから表示用モジュール名を取り出す。"""
    for key in ("module", "name", "pathname", "filename"):
        value = _read_value(record, key)
        if value:
            text = str(value).replace("\\", "/").rstrip("/")
            return text.rsplit("/", 1)[-1] or "unknown"
    return "unknown"


def format_function_name(record: Any) -> str:
    """LogRecord風オブジェクトから表示用関数名を取り出す。"""
    value = _read_value(record, "funcName") or _read_value(record, "function")
    text = str(value).strip() if value else ""
    return text or "<module>"


def format_line_number(record: Any) -> str:
    """LogRecord風オブジェクトから表示用行番号を取り出す。"""
    value = _read_value(record, "lineno") or _read_value(record, "line")
    try:
        line = int(value)
    except (TypeError, ValueError):
        return "?"
    return str(line) if line > 0 else "?"


def build_source_location(record: Any) -> SourceLocation:
    """表示用に整えた発生場所情報をまとめる。"""
    line_text = format_line_number(record)
    return SourceLocation(
        module=format_module_name(record),
        function=format_function_name(record),
        line=int(line_text) if line_text.isdigit() else None,
    )


def format_source_location(record: Any, *, style: str = "compact") -> str:
    """ログ発生場所を原因追跡しやすい一つの文字列へ整える。"""
    location = build_source_location(record)
    line = str(location.line) if location.line is not None else "?"
    if style == "path":
        return f"{location.module}::{location.function}:{line}"
    if style == "plain":
        return f"{location.module} {location.function} line {line}"
    return f"[{location.module}.{location.function}:{line}]"


def format_source_from_frame(frame: FrameType, *, style: str = "compact") -> str:
    """logging.LogRecordを作る前のフレームから発生場所文字列を作る。"""
    record = {
        "module": frame.f_globals.get("__name__", "unknown"),
        "funcName": frame.f_code.co_name,
        "lineno": frame.f_lineno,
    }
    return format_source_location(record, style=style)


def _read_value(record: Any, key: str) -> Any:
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)
