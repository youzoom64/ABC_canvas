# powan_id: node-0f77099d1c
# title: ハンドラー列正規化
# parent: node-e4916a59ac
# powanKind: organ
# codeLanguage: python

import logging
from collections.abc import Iterable
from typing import Tuple, Union


def normalize_handlers(
    handlers: Union[logging.Handler, Iterable[logging.Handler]],
) -> Tuple[logging.Handler, ...]:
    """Normalize one handler or an iterable of handlers into a tuple.

    Args:
        handlers: A single logging.Handler instance, or an iterable containing
            only logging.Handler instances.

    Returns:
        A tuple of logging.Handler instances.

    Raises:
        TypeError: If handlers is neither a logging.Handler nor an iterable of
            logging.Handler instances, or if any iterable element is invalid.
    """
    if isinstance(handlers, logging.Handler):
        return (handlers,)

    if not isinstance(handlers, Iterable):
        raise TypeError(
            "handlers must be a logging.Handler or an iterable of logging.Handler instances"
        )

    normalized = tuple(handlers)
    for index, handler in enumerate(normalized):
        if not isinstance(handler, logging.Handler):
            raise TypeError(
                f"handlers[{index}] must be a logging.Handler instance, got {type(handler).__name__}"
            )

    return normalized
