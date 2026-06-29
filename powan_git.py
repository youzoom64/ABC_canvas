from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable


LogFn = Callable[[str, str, dict[str, Any] | None], None]

HISTORY_DIR_NAME = ".powan_history"
SNAPSHOT_SCHEMA = 1

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def _node_name(node: dict[str, Any] | None, fallback_id: str | None = None) -> str:
    if node:
        title = str(node.get("title") or "").strip()
        body = str(node.get("body") or "").strip()
        if title:
            return title
        if body:
            return body.splitlines()[0][:40]
        node_id = str(node.get("id") or "").strip()
        if node_id:
            return node_id
    return fallback_id or "unknown"


def _parent_name(snapshot: dict[str, Any], parent_id: str | None) -> str:
    if not parent_id:
        return "最上位"
    node = (snapshot.get("nodesById") or {}).get(parent_id)
    return _node_name(node, parent_id)


def _clean_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def semantic_snapshot(document_name: str, document: dict[str, Any]) -> dict[str, Any]:
    raw_nodes = [
        node
        for node in (document.get("nodes") or [])
        if isinstance(node, dict) and str(node.get("id") or "").strip()
    ]
    ids = {str(node.get("id") or "") for node in raw_nodes}
    children_by_parent: dict[str, list[str]] = {node_id: [] for node_id in ids}
    for node in raw_nodes:
        node_id = str(node.get("id") or "")
        parent_id = str(node.get("parent") or "").strip()
        if parent_id and parent_id in ids and parent_id != node_id:
            children_by_parent.setdefault(parent_id, []).append(node_id)
    normalized_nodes: list[dict[str, Any]] = []
    for node in raw_nodes:
        node_id = str(node.get("id") or "")
        parent_id = str(node.get("parent") or "").strip()
        normalized_nodes.append(
            {
                "id": node_id,
                "title": _clean_text(node.get("title")),
                "body": _clean_text(node.get("body")),
                "powanKind": str(node.get("powanKind") or ""),
                "parent": parent_id if parent_id in ids and parent_id != node_id else None,
                "children": sorted(set(children_by_parent.get(node_id, []))),
                "codeLanguage": str(node.get("codeLanguage") or ""),
                "code": _clean_text(node.get("code")),
                "designMarkdown": _clean_text(node.get("designMarkdown")),
            }
        )
    normalized_nodes.sort(key=lambda item: item["id"])
    return {
        "schema": SNAPSHOT_SCHEMA,
        "document": document_name,
        "nodes": normalized_nodes,
        "nodesById": {node["id"]: node for node in normalized_nodes},
    }


def _diff_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for key in ("title", "body", "powanKind"):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


def semantic_diff(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    previous_nodes = (previous or {}).get("nodesById") or {}
    current_nodes = current.get("nodesById") or {}
    previous_ids = set(previous_nodes)
    current_ids = set(current_nodes)
    added_ids = sorted(current_ids - previous_ids)
    deleted_ids = sorted(previous_ids - current_ids)
    shared_ids = sorted(previous_ids & current_ids)

    added = [current_nodes[node_id] for node_id in added_ids]
    deleted = [previous_nodes[node_id] for node_id in deleted_ids]
    moved = [
        {
            "node": current_nodes[node_id],
            "from": previous_nodes[node_id].get("parent"),
            "to": current_nodes[node_id].get("parent"),
        }
        for node_id in shared_ids
        if previous_nodes[node_id].get("parent") != current_nodes[node_id].get("parent")
    ]
    code_changed = [
        current_nodes[node_id]
        for node_id in shared_ids
        if (
            previous_nodes[node_id].get("code") != current_nodes[node_id].get("code")
            or previous_nodes[node_id].get("codeLanguage") != current_nodes[node_id].get("codeLanguage")
        )
    ]
    design_changed = [
        current_nodes[node_id]
        for node_id in shared_ids
        if previous_nodes[node_id].get("designMarkdown") != current_nodes[node_id].get("designMarkdown")
    ]
    edited = [
        {
            "node": current_nodes[node_id],
            "fields": _diff_fields(previous_nodes[node_id], current_nodes[node_id]),
        }
        for node_id in shared_ids
        if _diff_fields(previous_nodes[node_id], current_nodes[node_id])
    ]
    return {
        "added": added,
        "deleted": deleted,
        "moved": moved,
        "codeChanged": code_changed,
        "designChanged": design_changed,
        "edited": edited,
    }


def diff_has_changes(diff: dict[str, Any]) -> bool:
    return any(diff.get(key) for key in ("added", "deleted", "moved", "codeChanged", "designChanged", "edited"))


def _count(diff: dict[str, Any], key: str) -> int:
    value = diff.get(key)
    return len(value) if isinstance(value, list) else 0


def commit_subject(diff: dict[str, Any]) -> str:
    return (
        "ポワン変更:"
        f" 追加 {_count(diff, 'added')}"
        f" 削除 {_count(diff, 'deleted')}"
        f" 移動 {_count(diff, 'moved')}"
        f" コード {_count(diff, 'codeChanged')}"
        f" 設計 {_count(diff, 'designChanged')}"
        f" 編集 {_count(diff, 'edited')}"
    )


def _list_lines(label: str, rows: list[str]) -> list[str]:
    if not rows:
        return [f"{label}: なし"]
    return [f"{label}:", *[f"- {row}" for row in rows]]


def _field_label(field: str) -> str:
    labels = {
        "title": "名前",
        "body": "意味",
        "powanKind": "種類",
    }
    return labels.get(field, field)


def commit_message(document_name: str, previous: dict[str, Any] | None, current: dict[str, Any], diff: dict[str, Any]) -> str:
    lines = [commit_subject(diff), "", f"ファイル: {document_name}", ""]
    lines.extend(_list_lines("追加", [_node_name(node, node.get("id")) for node in diff["added"]]))
    lines.append("")
    lines.extend(_list_lines("削除", [_node_name(node, node.get("id")) for node in diff["deleted"]]))
    lines.append("")
    lines.extend(
        _list_lines(
            "移動",
            [
                f"{_node_name(item['node'], item['node'].get('id'))}: "
                f"{_parent_name(previous or {}, item.get('from'))} -> {_parent_name(current, item.get('to'))}"
                for item in diff["moved"]
            ],
        )
    )
    lines.append("")
    lines.extend(_list_lines("コード変更", [_node_name(node, node.get("id")) for node in diff["codeChanged"]]))
    lines.append("")
    lines.extend(_list_lines("設計変更", [_node_name(node, node.get("id")) for node in diff["designChanged"]]))
    lines.append("")
    lines.extend(
        _list_lines(
            "本文変更",
            [
                f"{_node_name(item['node'], item['node'].get('id'))}: "
                f"{', '.join(_field_label(field) for field in item['fields'])}"
                for item in diff["edited"]
            ],
        )
    )
    return "\n".join(lines).rstrip() + "\n"


class PowanGitHistory:
    def __init__(self, project_root: Path, log_event: LogFn) -> None:
        self.project_root = project_root
        self.history_root = project_root / HISTORY_DIR_NAME
        self.log_event = log_event

    def snapshot_path(self, document_name: str) -> Path:
        return self.history_root / "documents" / f"{Path(document_name).stem}.semantic.json"

    def _run_git(self, args: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.history_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _ensure_repo(self) -> None:
        self.history_root.mkdir(parents=True, exist_ok=True)
        if not (self.history_root / ".git").exists():
            result = self._run_git(["init"])
            if result.returncode != 0:
                raise RuntimeError(f"git init failed: {result.stderr.strip() or result.stdout.strip()}")
        self._run_git(["config", "user.name", "ABC Canvas"])
        self._run_git(["config", "user.email", "abc-canvas@local"])

    def _read_previous(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(snapshot, dict):
            return None
        snapshot.setdefault("nodesById", {str(node.get("id") or ""): node for node in snapshot.get("nodes") or []})
        return snapshot

    def commit_document(self, document_name: str, document: dict[str, Any]) -> dict[str, Any]:
        with _lock_for(self.history_root):
            self._ensure_repo()
            path = self.snapshot_path(document_name)
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = self._read_previous(path)
            current = semantic_snapshot(document_name, document)
            diff = semantic_diff(previous, current)
            if not diff_has_changes(diff):
                return {"status": "unchanged", "changed": False}

            snapshot_for_file = {key: value for key, value in current.items() if key != "nodesById"}
            path.write_text(
                json.dumps(snapshot_for_file, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            rel_path = path.relative_to(self.history_root).as_posix()
            result = self._run_git(["add", "--", rel_path])
            if result.returncode != 0:
                raise RuntimeError(f"git add failed: {result.stderr.strip() or result.stdout.strip()}")

            message_path = self.history_root / ".git" / "powan_commit_message.txt"
            message = commit_message(document_name, previous, current, diff)
            message_path.write_text(message, encoding="utf-8")
            try:
                result = self._run_git(["commit", "-F", str(message_path)])
            finally:
                try:
                    message_path.unlink()
                except OSError:
                    pass
            if result.returncode != 0:
                raise RuntimeError(f"git commit failed: {result.stderr.strip() or result.stdout.strip()}")
            return {
                "status": "committed",
                "changed": True,
                "subject": commit_subject(diff),
                "snapshot": rel_path,
            }
