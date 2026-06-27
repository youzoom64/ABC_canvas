# powan_id: node-d7cd5dced1
# title: 例外型名抽出
# parent: node-efe6206313
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def exception_type_name(exc: BaseException, *, qualified: bool = False) -> str:
    """Return a stable display name for an exception type."""
    cls = type(exc)
    if qualified:
        return f"{cls.__module__}.{cls.__qualname__}"
    return cls.__name__
