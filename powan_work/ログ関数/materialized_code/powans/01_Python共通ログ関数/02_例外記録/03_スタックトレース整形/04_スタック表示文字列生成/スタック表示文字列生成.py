# powan_id: node-33644fd260
# title: スタック表示文字列生成
# parent: node-3d1cd44337
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from typing import Any


def stack_text(frames: list[dict[str, Any]]) -> str:
    """Build a compact human-readable stack trace from frame dictionaries."""
    lines: list[str] = []
    for frame in frames:
        lines.append(f"File {frame.get('filename')}, line {frame.get('line_number')}, in {frame.get('function')}")
        code = str(frame.get("line") or "").strip()
        if code:
            lines.append(f"  {code}")
    return "\n".join(lines)
