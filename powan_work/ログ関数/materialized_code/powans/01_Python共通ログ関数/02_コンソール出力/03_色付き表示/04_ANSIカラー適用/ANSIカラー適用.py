# powan_id: node-ef82582f4e
# title: ANSIカラー適用
# parent: node-7a3dcd5794
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any


def apply_ansi_color(text: Any, color_code: str | None) -> str:
    """Return text prefixed with an ANSI color code when one is provided.

    The function is intentionally small and side-effect free: callers decide
    whether color is enabled and which code to use, while this organ only
    performs the safe prefix operation.
    """
    value = str(text)
    prefix = str(color_code or "")
    return f"{prefix}{value}" if prefix else value


def default_apply_ansi_color(text: Any, color_code: str | None) -> str:
    """Compatibility alias for the parent color pipeline."""
    return apply_ansi_color(text, color_code)


__all__ = ["apply_ansi_color", "default_apply_ansi_color"]
