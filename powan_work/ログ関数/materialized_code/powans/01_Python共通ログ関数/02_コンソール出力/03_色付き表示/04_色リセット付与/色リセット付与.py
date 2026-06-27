# powan_id: node-b68db141e1
# title: 色リセット付与
# parent: node-7a3dcd5794
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

RESET = "\u001b[0m"


def append_color_reset(text: object) -> str:
    """Append one ANSI reset code so later console output does not inherit color."""
    value = str(text)
    if not value or value.endswith(RESET):
        return value
    return f"{value}{RESET}"


def default_append_reset(text: object) -> str:
    """Compatibility wrapper for the parent colorized-output pipeline."""
    return append_color_reset(text)


__all__ = ["RESET", "append_color_reset", "default_append_reset"]
