# powan_id: node-bca7963924
# title: フォーマット設計
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

"""Format design nerve for readable log lines.

This nerve powan combines three organ responsibilities into one stable
interface: which fields exist, how they are ordered, and how each field is
separated or wrapped. The parent formatter can call build_log_format_design()
and then format_log_line(record) without needing to know those details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class LogFieldSpec:
    """One visible item that may appear in a log line."""

    key: str
    label: str
    required: bool = True
    default: str = "-"


@dataclass(frozen=True)
class SeparatorSpec:
    """Characters used to join and decorate log fields."""

    field_separator: str = " | "
    message_separator: str = " - "
    bracketed_keys: tuple[str, ...] = ("level",)
    bracket_open: str = "["
    bracket_close: str = "]"


@dataclass(frozen=True)
class LogFormatDesign:
    """Complete display contract for a readable log line."""

    fields: tuple[LogFieldSpec, ...]
    order: tuple[str, ...]
    separators: SeparatorSpec

    def validate(self) -> None:
        field_keys = {field.key for field in self.fields}
        unknown = [key for key in self.order if key not in field_keys]
        if unknown:
            raise ValueError(f"Unknown ordered log field(s): {', '.join(unknown)}")

        missing = [field.key for field in self.fields if field.required and field.key not in self.order]
        if missing:
            raise ValueError(f"Required log field(s) missing from order: {', '.join(missing)}")

    def normalize_record(self, record: Mapping[str, object]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        defaults = {field.key: field.default for field in self.fields}
        for key in self.order:
            value = record.get(key, defaults.get(key, "-"))
            normalized[key] = defaults.get(key, "-") if value is None or value == "" else str(value)
        return normalized

    def decorate(self, key: str, value: str) -> str:
        if key in self.separators.bracketed_keys:
            return f"{self.separators.bracket_open}{value}{self.separators.bracket_close}"
        return value

    def format_line(self, record: Mapping[str, object]) -> str:
        self.validate()
        normalized = self.normalize_record(record)
        prefix_parts: list[str] = []
        message = ""
        for key in self.order:
            value = self.decorate(key, normalized[key])
            if key == "message":
                message = value
            else:
                prefix_parts.append(value)
        prefix = self.separators.field_separator.join(prefix_parts)
        return f"{prefix}{self.separators.message_separator}{message}" if prefix else message


def define_display_fields() -> tuple[LogFieldSpec, ...]:
    return (
        LogFieldSpec("timestamp", "日時"),
        LogFieldSpec("level", "ログレベル"),
        LogFieldSpec("app", "アプリ名"),
        LogFieldSpec("module", "モジュール名"),
        LogFieldSpec("line", "行番号", required=False),
        LogFieldSpec("message", "メッセージ"),
    )


def define_display_order(fields: Sequence[LogFieldSpec]) -> tuple[str, ...]:
    preferred = ("timestamp", "level", "app", "module", "line", "message")
    field_keys = {field.key for field in fields}
    return tuple(key for key in preferred if key in field_keys)


def define_separators() -> SeparatorSpec:
    return SeparatorSpec()


def build_log_format_design() -> LogFormatDesign:
    fields = define_display_fields()
    design = LogFormatDesign(
        fields=fields,
        order=define_display_order(fields),
        separators=define_separators(),
    )
    design.validate()
    return design


def format_log_line(record: Mapping[str, object]) -> str:
    return build_log_format_design().format_line(record)
