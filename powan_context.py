from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_CODE_LIMIT = 12000
POWAN_KIND_DEFAULT = "nerve"


def powan_kind(node: dict[str, Any] | None) -> str:
    if not node:
        return ""
    value = str(node.get("powanKind") or "").strip()
    if value in {"organ", "臓器"}:
        return "organ"
    return POWAN_KIND_DEFAULT


def build_powan_context(
    *,
    project: str,
    document_name: str,
    document: dict[str, Any],
    node_id: str,
    conversation: dict[str, Any] | None = None,
    messages: list[dict[str, Any]] | None = None,
    user_text: str | None = None,
    code_limit: int = DEFAULT_CODE_LIMIT,
    include_meaning_tree: bool = False,
    include_direct_child_code: bool = False,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    nodes = valid_nodes(document)
    node = find_node(nodes, node_id)
    parent = find_node(nodes, node.get("parent")) if node else None
    children = direct_children(nodes, node_id)
    context = {
        "globalDepth": global_depth(nodes, node_id),
        "powan": summarize_powan_for_prompt(node, code_limit=code_limit),
        "parent": summarize_powan_for_prompt(parent, code_limit=code_limit),
        "children": [summarize_powan_for_prompt(child, code_limit=code_limit) for child in children],
        "userText": user_text or "",
    }
    if children:
        context["childCommandTemplate"] = build_child_command_template(children)
    if include_meaning_tree:
        context["meaningTree"] = build_meaning_tree_text(document, node_id)
    if include_direct_child_code:
        context["codeWriteMode"] = True
        context["directChildCode"] = summarize_direct_child_code_for_prompt(children, code_limit=code_limit)
    clean_attachments = summarize_attachments_for_prompt(attachments or [])
    if clean_attachments:
        context["attachments"] = clean_attachments
    return context


def valid_nodes(document: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = document.get("nodes") or []
    return [node for node in nodes if isinstance(node, dict) and not is_archived(node)]


def is_archived(node: dict[str, Any] | None) -> bool:
    return bool(node and node.get("archived"))


def find_node(nodes: list[dict[str, Any]], node_id: str | None) -> dict[str, Any] | None:
    if not node_id:
        return None
    for node in nodes:
        if str(node.get("id")) == str(node_id):
            return node
    return None


def direct_children(nodes: list[dict[str, Any]], node_id: str | None) -> list[dict[str, Any]]:
    if not node_id:
        return []
    return [node for node in nodes if str(node.get("parent")) == str(node_id)]


def global_depth(nodes: list[dict[str, Any]], node_id: str | None) -> int:
    node = find_node(nodes, node_id)
    if not node:
        return 0
    node_by_id = {str(item.get("id")): item for item in nodes if item.get("id") is not None}
    depth = 0
    seen: set[str] = set()
    current = node
    while current.get("parent"):
        parent_id = str(current.get("parent"))
        if parent_id in seen:
            break
        parent = node_by_id.get(parent_id)
        if not parent:
            break
        seen.add(parent_id)
        depth += 1
        current = parent
    return depth


def summarize_powan(
    node: dict[str, Any] | None,
    *,
    code_limit: int = DEFAULT_CODE_LIMIT,
    include_visual: bool = True,
) -> dict[str, Any]:
    if not node:
        return {}
    code = str(node.get("code") or "")
    summary: dict[str, Any] = {
        "id": node.get("id"),
        "meaning": meaning_text(node),
        "title": node.get("title") or "",
        "body": node.get("body") or "",
        "powanKind": powan_kind(node),
        "codeLanguage": node.get("codeLanguage") or "auto",
        "hasCode": bool(code.strip()),
        "code": limit_text(code, code_limit),
        "parent": node.get("parent"),
        "children": list(node.get("children") or []),
    }
    if include_visual:
        summary["layout"] = deepcopy(node.get("layout") or {})
        summary["style"] = deepcopy(node.get("style") or {})
    if is_archived(node):
        summary["archived"] = True
        summary["archivedAt"] = node.get("archivedAt")
        summary["archivedParent"] = node.get("archivedParent")
    return summary


def summarize_powan_for_prompt(
    node: dict[str, Any] | None,
    *,
    code_limit: int = DEFAULT_CODE_LIMIT,
) -> dict[str, Any]:
    if not node:
        return blank_prompt_powan()
    code = str(node.get("code") or "")
    return {
        "meaning": meaning_text(node),
        "title": node.get("title") or "",
        "body": node.get("body") or "",
        "powanKind": powan_kind(node),
        "codeLanguage": node.get("codeLanguage") or "",
        "hasCode": bool(code.strip()),
    }


def summarize_direct_child_code_for_prompt(
    children: list[dict[str, Any]],
    *,
    code_limit: int = DEFAULT_CODE_LIMIT,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for child in children:
        code = str(child.get("code") or "")
        if not code.strip():
            continue
        items.append(
            {
                "meaning": meaning_text(child),
                "title": child.get("title") or "",
                "body": child.get("body") or "",
                "powanKind": powan_kind(child),
                "codeLanguage": child.get("codeLanguage") or "",
                "code": limit_text(code, code_limit),
            }
        )
    return items


def build_child_command_template(children: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "purpose": "直下の子ポワンへ個別指示をまとめて渡すためのJSON。対象の子はinstructionsのinstructionを埋め、対象外の子はskip:trueとskipReasonを入れて、command-childrenを一回だけ実行してください。",
        "command": "python .agents/skills/abc-powan/scripts/abc_powan_tool.py command-children --stdin-json",
        "important": "子ごとにcommand-child-powanを繰り返さないでください。対象外の子へ「対象外です」という会話は送らずskip:trueにしてください。受信後はアプリが対象分だけDBへ保存し、0.1秒ごとに開始します。",
        "json": {
            "instruction": "",
            "instructions": [
                {
                    "childId": str(child.get("id") or ""),
                    "title": str(child.get("title") or ""),
                    "instruction": "",
                    "skip": False,
                    "skipReason": "",
                }
                for child in children
            ],
            "includeMeaningTree": False,
        },
    }


def build_meaning_tree_text(document: dict[str, Any], current_node_id: str | None) -> str:
    nodes = valid_nodes(document)
    if not nodes:
        return "（ポワンなし）"

    node_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        node_id = str(node.get("id") or "")
        if node_id:
            node_by_id[node_id] = node

    children_by_parent: dict[str, list[dict[str, Any]]] = {}
    roots: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("id") or "")
        parent_id = str(node.get("parent") or "")
        if parent_id and parent_id in node_by_id and parent_id != node_id:
            children_by_parent.setdefault(parent_id, []).append(node)
        else:
            roots.append(node)

    lines: list[str] = []
    visited: set[str] = set()
    current_id = str(current_node_id or "")

    def walk(node: dict[str, Any], depth: int) -> None:
        node_id = str(node.get("id") or "")
        if node_id and node_id in visited:
            return
        if node_id:
            visited.add(node_id)
        marker = " ここがあなた！" if node_id and node_id == current_id else ""
        lines.append(f"{'  ' * depth}- {meaning_tree_label(node)}{marker}")
        for child in children_by_parent.get(node_id, []):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)

    for node in nodes:
        node_id = str(node.get("id") or "")
        if node_id and node_id not in visited:
            walk(node, 0)

    return "\n".join(lines)


def meaning_tree_label(node: dict[str, Any]) -> str:
    label = str(node.get("title") or node.get("body") or "").strip()
    return label or "名前のないポワン"


def summarize_attachments_for_prompt(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for attachment in attachments[:20]:
        if not isinstance(attachment, dict):
            continue
        summary: dict[str, Any] = {}
        for key in ("kind", "source", "name", "mime", "size", "path", "relativePath", "url", "host"):
            value = attachment.get(key)
            if value not in (None, ""):
                summary[key] = value
        summary["pathAvailable"] = bool(summary.get("path"))
        if summary:
            summaries.append(summary)
    return summaries


def blank_prompt_powan() -> dict[str, Any]:
    return {
        "meaning": "",
        "title": "",
        "body": "",
        "powanKind": "",
        "codeLanguage": "",
        "hasCode": False,
    }


def meaning_text(node: dict[str, Any]) -> str:
    return str(node.get("body") or node.get("title") or "").strip()


def limit_text(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... truncated {len(text) - limit} chars ..."
