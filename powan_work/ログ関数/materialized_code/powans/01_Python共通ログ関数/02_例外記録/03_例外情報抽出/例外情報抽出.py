# powan_id: node-efe6206313
# title: 例外情報抽出
# parent: node-76c5714ad9
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from typing import Any


def extract_exception_info(exc: BaseException, *, include_chain: bool = True, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Collect readable exception facts for exception logging."""
    info: dict[str, Any] = {
        "type": type(exc).__name__,
        "module": type(exc).__module__,
        "qualified_type": f"{type(exc).__module__}.{type(exc).__qualname__}",
        "message": str(exc),
    }
    if include_chain:
        chain: list[dict[str, str]] = []
        seen: set[int] = set()
        current = exc.__cause__ or exc.__context__
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            chain.append({"type": type(current).__name__, "message": str(current)})
            current = current.__cause__ or current.__context__
        info["chain"] = chain
    if extra:
        info["extra"] = dict(extra)
    return info
