# powan_id: node-bd986ca92f
# title: 長すぎるスタックの省略
# parent: node-3d1cd44337
# powanKind: organ
# codeLanguage: python

from __future__ import annotations


def trim_stack_lines(text: str, *, max_lines: int = 80, head: int = 30, tail: int = 30) -> str:
    """Keep long stack traces readable by preserving the beginning and end."""
    lines = text.splitlines()
    if max_lines <= 0 or len(lines) <= max_lines:
        return text
    head = max(0, min(head, max_lines))
    tail = max(0, min(tail, max_lines - head - 1))
    omitted = len(lines) - head - tail
    return "\n".join([*lines[:head], f"... omitted {omitted} stack lines ...", *lines[-tail:]])
