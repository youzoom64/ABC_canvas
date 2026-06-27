# powan_id: node-6a3578c9ca
# title: ログレベル表示情報
# parent: node-86bf66c54a
# powanKind: organ
# codeLanguage: python

"""ログレベル表示情報を返す臓器ポワン。"""
from __future__ import annotations

_DISPLAY_INFO = {
    "trace": {"level": "trace", "display_name": "TRACE", "short_name": "TRC", "color": "bright_black", "icon": ".", "weight": 5},
    "debug": {"level": "debug", "display_name": "DEBUG", "short_name": "DBG", "color": "cyan", "icon": "D", "weight": 10},
    "info": {"level": "info", "display_name": "INFO", "short_name": "INF", "color": "green", "icon": "i", "weight": 20},
    "warning": {"level": "warning", "display_name": "WARNING", "short_name": "WARN", "color": "yellow", "icon": "!", "weight": 30},
    "error": {"level": "error", "display_name": "ERROR", "short_name": "ERR", "color": "red", "icon": "x", "weight": 40},
    "critical": {"level": "critical", "display_name": "CRITICAL", "short_name": "CRIT", "color": "bright_red", "icon": "!!", "weight": 50},
}

_ALIASES = {"warn": "warning", "fatal": "critical", "crit": "critical", "err": "error", "dbg": "debug", "trc": "trace", "inf": "info"}


def get_display_info(level: str) -> dict[str, object]:
    key = _ALIASES.get(str(level).strip().lower(), str(level).strip().lower())
    try:
        return dict(_DISPLAY_INFO[key])
    except KeyError as exc:
        raise ValueError(f"unknown log level: {level!r}") from exc
