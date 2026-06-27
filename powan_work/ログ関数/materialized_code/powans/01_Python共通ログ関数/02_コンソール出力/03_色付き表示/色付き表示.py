# powan_id: node-7a3dcd5794
# title: 色付き表示
# parent: node-30e768b421
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, TextIO
import os
import sys

RESET = "\033[0m"

ColorEnabledDecider = Callable[..., bool]
LevelColorSelector = Callable[[str], str]
AnsiColorApplier = Callable[[str, str], str]
ResetAppender = Callable[[str], str]


@dataclass(frozen=True)
class ColorizedMessage:
    text: str
    level: str
    color_enabled: bool
    color_code: str


def default_color_enabled(
    *,
    stream: TextIO | None = None,
    force_color: bool | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Decide whether ANSI color should be emitted for this console."""
    if force_color is not None:
        return bool(force_color)

    env_map = os.environ if env is None else env
    if env_map.get("NO_COLOR") is not None:
        return False
    if env_map.get("FORCE_COLOR"):
        return True

    target = stream if stream is not None else sys.stdout
    isatty = getattr(target, "isatty", None)
    return bool(isatty and isatty())


def default_level_color(level: str) -> str:
    """Return an ANSI color sequence for a normalized log level."""
    normalized = str(level or "info").strip().lower()
    colors = {
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
    return colors.get(normalized, colors["info"])


def default_apply_ansi_color(text: str, color_code: str) -> str:
    """Prefix text with an ANSI color code when one is available."""
    value = str(text)
    return f"{color_code}{value}" if color_code else value


def default_append_reset(text: str) -> str:
    """Append ANSI reset once so later console output does not inherit color."""
    value = str(text)
    if not value or value.endswith(RESET):
        return value
    return f"{value}{RESET}"


def colorize_for_console(
    text: Any,
    level: str = "info",
    *,
    stream: TextIO | None = None,
    force_color: bool | None = None,
    env: Mapping[str, str] | None = None,
    color_enabled_decider: ColorEnabledDecider = default_color_enabled,
    level_color_selector: LevelColorSelector = default_level_color,
    ansi_color_applier: AnsiColorApplier = default_apply_ansi_color,
    reset_appender: ResetAppender = default_append_reset,
) -> ColorizedMessage:
    """Bundle child color helpers into one safe console-color pipeline."""
    plain_text = str(text)
    normalized_level = str(level or "info").strip().lower()
    enabled = color_enabled_decider(stream=stream, force_color=force_color, env=env)

    if not enabled:
        return ColorizedMessage(
            text=plain_text,
            level=normalized_level,
            color_enabled=False,
            color_code="",
        )

    color_code = level_color_selector(normalized_level)
    colored = ansi_color_applier(plain_text, color_code)
    safe_colored = reset_appender(colored) if color_code else colored
    return ColorizedMessage(
        text=safe_colored,
        level=normalized_level,
        color_enabled=True,
        color_code=color_code,
    )


def format_console_text(text: Any, level: str = "info", **kwargs: Any) -> str:
    """Return only the display text for callers that do not need metadata."""
    return colorize_for_console(text, level, **kwargs).text


__all__ = [
    "ColorizedMessage",
    "colorize_for_console",
    "format_console_text",
    "default_color_enabled",
    "default_level_color",
    "default_apply_ansi_color",
    "default_append_reset",
]
