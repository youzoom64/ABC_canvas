# powan_id: node-d55d2d6cc4
# title: 例外メッセージ抽出
# parent: node-efe6206313
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def exception_message(exc: BaseException, *, fallback: str = "<no exception message>") -> str:
    """Safely stringify an exception message."""
    try:
        message = str(exc)
    except Exception as stringify_error:
        message = f"<failed to stringify exception: {type(stringify_error).__name__}>"
    return message if message else fallback
