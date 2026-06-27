# powan_id: node-1e80d3461c
# title: レベル別カラー選択
# parent: node-7a3dcd5794
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Mapping

LEVEL_COLORS: Mapping[str, str] = {
    "trace": "\033[90m",
    "debug": "\033[36m",
    "info": "\033[32m",
    "notice": "\033[34m",
    "warning": "\033[33m",
    "warn": "\033[33m",
    "error": "\033[31m",
    "critical": "\033[1;31m",
    "fatal": "\033[1;31m",
}


def select_level_color(level: object) -> str:
    """Return the ANSI color code for a known log level, or an empty string."""
    normalized = str(level or "").strip().lower()
    return LEVEL_COLORS.get(normalized, "")


def default_level_color(level: object) -> str:
    """Compatibility alias for callers that expect the parent helper name."""
    return select_level_color(level)


__all__ = ["LEVEL_COLORS", "select_level_color", "default_level_color"]
