# powan_id: node-e248375f07
# title: 例外チェーン抽出
# parent: node-efe6206313
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def exception_chain(exc: BaseException, *, limit: int = 20) -> list[dict[str, str]]:
    """Return cause/context exceptions in order without infinite loops."""
    chain: list[dict[str, str]] = []
    seen: set[int] = set()
    current = exc.__cause__ or exc.__context__
    while current is not None and id(current) not in seen and len(chain) < limit:
        seen.add(id(current))
        relation = "cause" if current is exc.__cause__ else "context"
        chain.append({"relation": relation, "type": type(current).__name__, "message": str(current)})
        current = current.__cause__ or current.__context__
    return chain
