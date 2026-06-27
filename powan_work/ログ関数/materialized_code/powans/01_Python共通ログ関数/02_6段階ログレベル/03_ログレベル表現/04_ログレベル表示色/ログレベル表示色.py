# powan_id: node-58d724dad2
# title: ログレベル表示色
# parent: node-86bf66c54a
# powanKind: organ
# codeLanguage: python

"""ログレベル表示色を返す臓器ポワン。"""
from __future__ import annotations

_COLORS = {
    "trace": "bright_black",
    "debug": "cyan",
    "info": "green",
    "warning": "yellow",
    "error": "red",
    "critical": "bright_red",
}
_EMPHASIS = {
    "trace": 0,
    "debug": 1,
    "info": 1,
    "warning": 2,
    "error": 3,
    "critical": 4,
}
_ALIASES = {"warn": "warning", "fatal": "critical", "crit": "critical", "err": "error", "dbg": "debug", "trc": "trace", "inf": "info"}


def get_level_color(level: str) -> str:
    key = _ALIASES.get(str(level).strip().lower(), str(level).strip().lower())
    try:
        return _COLORS[key]
    except KeyError as exc:
        raise ValueError(f"unknown log level: {level!r}") from exc


def get_level_emphasis(level: str) -> int:
    key = _ALIASES.get(str(level).strip().lower(), str(level).strip().lower())
    try:
        return _EMPHASIS[key]
    except KeyError as exc:
        raise ValueError(f"unknown log level: {level!r}") from exc
