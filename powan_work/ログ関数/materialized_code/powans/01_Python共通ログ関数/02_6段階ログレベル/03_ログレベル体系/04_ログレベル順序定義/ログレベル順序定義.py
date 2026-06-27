# powan_id: node-e6c287adf8
# title: ログレベル順序定義
# parent: node-defe15d75c
# powanKind: organ
# codeLanguage: python

"""Ordering rules for the six supported logging levels."""

from __future__ import annotations

from typing import Final, Mapping

LOG_LEVEL_ORDERED_NAMES: Final[tuple[str, ...]] = (
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
)

LOG_LEVEL_ORDER: Final[Mapping[str, int]] = {
    name: index for index, name in enumerate(LOG_LEVEL_ORDERED_NAMES)
}


def order_index(level: str) -> int:
    """Return the ordering index for a canonical level name."""

    normalized = level.lower()
    try:
        return LOG_LEVEL_ORDER[normalized]
    except KeyError as exc:
        raise KeyError(f"Unsupported log level: {level!r}") from exc


def is_at_least(level: str, minimum: str) -> bool:
    """Return True when level is as strong as minimum or stronger."""

    return order_index(level) >= order_index(minimum)
