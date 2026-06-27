# powan_id: node-7dd49ccb60
# title: 区切り文字定義
# parent: node-bca7963924
# powanKind: organ
# codeLanguage: python

"""Separator definition organ for log formatting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeparatorSpec:
    field_separator: str = " | "
    message_separator: str = " - "
    bracketed_keys: tuple[str, ...] = ("level",)
    bracket_open: str = "["
    bracket_close: str = "]"

    def decorate(self, key: str, value: str) -> str:
        if key in self.bracketed_keys:
            return f"{self.bracket_open}{value}{self.bracket_close}"
        return value


def define_separators() -> SeparatorSpec:
    """Return the readable separators and wrappers used in one log line."""

    return SeparatorSpec()
