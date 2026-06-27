# powan_id: node-86bf66c54a
# title: ログレベル表現
# parent: node-5815509426
# powanKind: nerve
# codeLanguage: python

"""ログレベル表現を束ねる神経ポワン。

このポワンは、6段階ログレベルを人間が見分けやすく表示するための
表示情報・短縮名・表示色をひとつのインターフェースとしてまとめます。
詳細な表示情報、短縮名、表示色は配下の臓器ポワンが担当できるよう、
ここでは安定した呼び出し形とフォールバック定義を持ちます。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class LogLevelPresentation:
    level: str
    display_name: str
    short_name: str
    color: str
    icon: str
    weight: int


_LEVEL_PRESENTATIONS: Mapping[str, LogLevelPresentation] = {
    "trace": LogLevelPresentation("trace", "TRACE", "TRC", "bright_black", ".", 5),
    "debug": LogLevelPresentation("debug", "DEBUG", "DBG", "cyan", "D", 10),
    "info": LogLevelPresentation("info", "INFO", "INF", "green", "i", 20),
    "warning": LogLevelPresentation("warning", "WARNING", "WARN", "yellow", "!", 30),
    "error": LogLevelPresentation("error", "ERROR", "ERR", "red", "x", 40),
    "critical": LogLevelPresentation("critical", "CRITICAL", "CRIT", "bright_red", "!!", 50),
}


def normalize_level_name(level: str) -> str:
    """表示系で使うログレベル名を小文字の標準名にそろえます。"""
    name = str(level).strip().lower()
    aliases = {
        "warn": "warning",
        "fatal": "critical",
        "crit": "critical",
        "err": "error",
        "dbg": "debug",
        "trc": "trace",
        "inf": "info",
    }
    return aliases.get(name, name)


def get_log_level_presentation(level: str) -> LogLevelPresentation:
    """表示名、短縮名、色、アイコンをまとめて返します。"""
    normalized = normalize_level_name(level)
    try:
        return _LEVEL_PRESENTATIONS[normalized]
    except KeyError as exc:
        known = ", ".join(_LEVEL_PRESENTATIONS)
        raise ValueError(f"unknown log level for presentation: {level!r}; expected one of {known}") from exc


def get_log_level_display_info(level: str) -> dict[str, object]:
    """UIやフォーマッターで扱いやすいdict形式の表示情報を返します。"""
    presentation = get_log_level_presentation(level)
    return {
        "level": presentation.level,
        "display_name": presentation.display_name,
        "short_name": presentation.short_name,
        "color": presentation.color,
        "icon": presentation.icon,
        "weight": presentation.weight,
    }


def get_log_level_short_name(level: str) -> str:
    """幅を抑えたログレベル短縮名を返します。"""
    return get_log_level_presentation(level).short_name


def get_log_level_color(level: str) -> str:
    """コンソールやUIで使うログレベル表示色名を返します。"""
    return get_log_level_presentation(level).color


def iter_log_level_presentations() -> tuple[LogLevelPresentation, ...]:
    """6段階ログレベルの表現情報を低い順に返します。"""
    return tuple(sorted(_LEVEL_PRESENTATIONS.values(), key=lambda item: item.weight))
