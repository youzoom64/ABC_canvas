# powan_id: node-e1c23ab428
# title: 設定済み判定
# parent: node-894cbd722f
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import logging
from typing import Final

DEFAULT_CONFIGURED_ATTR: Final[str] = "_abc_common_logger_configured"


def is_logger_configured(
    logger: logging.Logger,
    *,
    configured_attr: str = DEFAULT_CONFIGURED_ATTR,
) -> bool:
    """Return True when the shared get_logger setup was already applied.

    The logger acquisition entry calls this before preparing handlers again.
    A sibling setup powan marks the logger with the same private attribute
    after applying the shared level, handlers, and propagation settings.
    """
    if not isinstance(logger, logging.Logger):
        raise TypeError("logger must be a logging.Logger")
    if not isinstance(configured_attr, str):
        raise TypeError("configured_attr must be a string")
    if not configured_attr.strip():
        raise ValueError("configured_attr must not be empty")

    return bool(getattr(logger, configured_attr, False))


__all__ = ["DEFAULT_CONFIGURED_ATTR", "is_logger_configured"]
