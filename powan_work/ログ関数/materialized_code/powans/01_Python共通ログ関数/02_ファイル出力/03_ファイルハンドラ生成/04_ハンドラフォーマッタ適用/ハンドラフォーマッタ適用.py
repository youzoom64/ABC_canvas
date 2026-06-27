# powan_id: node-6545f6683e
# title: ハンドラフォーマッタ適用
# parent: node-82cb45e7df
# powanKind: organ
# codeLanguage: python

import logging


def apply_formatter(handler: logging.Handler, formatter: logging.Formatter | None) -> logging.Handler:
    if formatter is not None:
        handler.setFormatter(formatter)
    return handler
