# powan_id: node-8520668d50
# title: 対話端末判定
# parent: node-ffda89edb6
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import os
from typing import Mapping, TextIO

_COLOR_TERMS = {"xterm", "xterm-256color", "screen", "screen-256color", "vt100", "ansi"}


def inspect_console_terminal(
    stream: TextIO | None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    """Inspect whether a stream behaves like an interactive terminal."""

    env = environ if environ is not None else os.environ
    is_interactive = bool(getattr(stream, "isatty", lambda: False)()) if stream is not None else False

    no_color = "NO_COLOR" in env
    force_color = str(env.get("FORCE_COLOR", "")).strip().lower() not in {"", "0", "false", "no", "off"}
    term = str(env.get("TERM", "")).strip().lower()
    ansicon = "ANSICON" in env or "WT_SESSION" in env

    supports_color = False
    if force_color:
        supports_color = True
    elif is_interactive and not no_color:
        supports_color = ansicon or term in _COLOR_TERMS or "color" in term

    return {
        "is_interactive": is_interactive,
        "supports_color": supports_color,
    }
