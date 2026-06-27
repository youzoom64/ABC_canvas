# powan_id: node-237b353b32
# title: コンソール出力保護
# parent: node-30e768b421
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, TextIO


@dataclass(frozen=True)
class ConsoleOutputProtectionResult:
    """Result of preparing a logger for protected console output."""

    logger: logging.Logger
    handler: Optional[logging.Handler]
    duplicate_handler_found: bool
    encoding_policy: str
    fallback_enabled: bool


DuplicateHandlerPredicate = Callable[[logging.Logger, logging.Handler], bool]
FallbackWrapper = Callable[[logging.Handler], logging.Handler]
EncodingPolicyProvider = Callable[[], str]


def protect_console_output(
    logger: logging.Logger,
    handler: logging.Handler,
    *,
    is_duplicate_handler: DuplicateHandlerPredicate,
    encoding_policy: EncodingPolicyProvider,
    with_output_fallback: FallbackWrapper,
) -> ConsoleOutputProtectionResult:
    """Attach a console handler only when safe, with encoding policy and fallback applied.

    This nerve powan does not own the detailed checks. It connects the child
    responsibilities: duplicate handler detection, mojibake avoidance policy,
    and a last-resort output fallback.
    """

    policy = encoding_policy()
    duplicate = is_duplicate_handler(logger, handler)
    if duplicate:
        return ConsoleOutputProtectionResult(
            logger=logger,
            handler=None,
            duplicate_handler_found=True,
            encoding_policy=policy,
            fallback_enabled=False,
        )

    protected_handler = with_output_fallback(handler)
    logger.addHandler(protected_handler)
    return ConsoleOutputProtectionResult(
        logger=logger,
        handler=protected_handler,
        duplicate_handler_found=False,
        encoding_policy=policy,
        fallback_enabled=True,
    )


def ensure_console_output_is_protected(
    logger: logging.Logger,
    handler: logging.Handler,
    *,
    is_duplicate_handler: DuplicateHandlerPredicate,
    encoding_policy: EncodingPolicyProvider,
    with_output_fallback: FallbackWrapper,
) -> logging.Logger:
    """Prepare protected console output and return the logger for fluent setup."""

    protect_console_output(
        logger,
        handler,
        is_duplicate_handler=is_duplicate_handler,
        encoding_policy=encoding_policy,
        with_output_fallback=with_output_fallback,
    )
    return logger
