# powan_id: node-4eee556154
# title: ログレベル短縮名
# parent: node-86bf66c54a
# powanKind: organ
# codeLanguage: python

"""ログレベル短縮名を返す臓器ポワン。"""
from __future__ import annotations

_SHORT_NAMES = {
    "trace": "TRC",
    "debug": "DBG",
    "info": "INF",
    "warning": "WARN",
    "error": "ERR",
    "critical": "CRIT",
}
_ALIASES = {"warn": "warning", "fatal": "critical", "crit": "critical", "err": "error", "dbg": "debug", "trc": "trace", "inf": "info"}


def get_short_name(level: str) -> str:
    key = _ALIASES.get(str(level).strip().lower(), str(level).strip().lower())
    try:
        return _SHORT_NAMES[key]
    except KeyError as exc:
        raise ValueError(f"unknown log level: {level!r}") from exc
