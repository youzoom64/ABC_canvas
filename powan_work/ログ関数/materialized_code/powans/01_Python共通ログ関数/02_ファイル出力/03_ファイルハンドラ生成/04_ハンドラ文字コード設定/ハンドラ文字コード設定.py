# powan_id: node-fda3ccf172
# title: ハンドラ文字コード設定
# parent: node-82cb45e7df
# powanKind: organ
# codeLanguage: python

import logging


def get_handler_encoding(handler: logging.Handler, default: str = "utf-8") -> str:
    return str(getattr(handler, "encoding", None) or default)


def prefer_utf8_encoding(encoding: str | None = None) -> str:
    return encoding or "utf-8"
