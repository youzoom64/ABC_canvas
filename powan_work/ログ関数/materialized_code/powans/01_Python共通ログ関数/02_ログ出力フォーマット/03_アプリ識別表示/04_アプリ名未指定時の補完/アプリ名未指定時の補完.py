# powan_id: node-c1d3576b04
# title: アプリ名未指定時の補完
# parent: node-90c2d94129
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def fallback_app_name(app_name: str | None, logger_name: str | None, default: str = 'app') -> str:
    app = str(app_name or '').strip()
    if app:
        return app
    logger = str(logger_name or '').strip()
    return logger.split('.')[0] if logger else default
