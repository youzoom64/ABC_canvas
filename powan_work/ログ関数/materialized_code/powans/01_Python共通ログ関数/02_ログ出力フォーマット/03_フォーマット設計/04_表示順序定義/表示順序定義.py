# powan_id: node-49a1246556
# title: 表示順序定義
# parent: node-bca7963924
# powanKind: organ
# codeLanguage: python

"""Display order definition organ for log formatting."""

from __future__ import annotations

from typing import Iterable, Protocol


class HasLogKey(Protocol):
    key: str


STANDARD_DISPLAY_ORDER: tuple[str, ...] = (
    "timestamp",
    "level",
    "app",
    "module",
    "line",
    "message",
)


def define_display_order(fields: Iterable[HasLogKey]) -> tuple[str, ...]:
    """Order fields from broad context to the concrete message."""

    existing = {field.key for field in fields}
    ordered = tuple(key for key in STANDARD_DISPLAY_ORDER if key in existing)
    extras = tuple(sorted(existing - set(STANDARD_DISPLAY_ORDER)))
    return ordered + extras
