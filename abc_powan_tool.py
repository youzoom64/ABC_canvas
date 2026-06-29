from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_API_BASE = "http://127.0.0.1:8790"
DEFAULT_FILE = "project.powan"


class ToolError(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="ABC Canvas powan operation tool")
    parser.add_argument(
        "operation",
        choices=(
            "set-my-meaning",
            "create-child-powan",
            "create-powan-tree",
            "delete-child-powan",
            "restore-child-powan",
            "command-children",
            "command-child-powan",
            "read-powan-codes",
            "write-my-code",
        ),
    )
    parser.add_argument("--api-base", default=os.environ.get("ABC_CANVAS_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--project", default=os.environ.get("ABC_POWAN_PROJECT", ""))
    parser.add_argument("--file", default=os.environ.get("ABC_POWAN_FILE", DEFAULT_FILE))
    parser.add_argument("--node-id", default=os.environ.get("ABC_POWAN_NODE_ID", ""))
    parser.add_argument("--json", dest="json_path", default="")
    parser.add_argument("--stdin-json", action="store_true")
    parser.add_argument("--title", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--body-file", default="")
    parser.add_argument("--powan-kind", default="")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--code-language", default="")
    parser.add_argument("--code", default="")
    parser.add_argument("--code-file", default="")
    parser.add_argument("--child-id", default="")
    parser.add_argument("--target-parent-id", default="")
    parser.add_argument("--target-id", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--include-self", action="store_true")
    args = parser.parse_args()

    try:
        payload = request_payload(args)
        result = dispatch(args, payload)
    except ToolError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


def request_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_payload(args)
    if args.title:
        payload["title"] = args.title
    if args.body:
        payload["body"] = args.body
    if args.body_file:
        payload["body"] = read_text_file(args.body_file)
    if args.powan_kind:
        payload["powanKind"] = args.powan_kind
    if args.instruction:
        payload["instruction"] = args.instruction
    if args.code_language:
        payload["codeLanguage"] = args.code_language
    if args.code:
        payload["code"] = args.code
    if args.code_file:
        payload["code"] = read_text_file(args.code_file)
    if args.child_id:
        payload["childId"] = args.child_id
    if args.target_parent_id:
        payload["targetParentId"] = args.target_parent_id
    if args.target_id:
        payload["targetId"] = args.target_id
    if args.path:
        payload["path"] = [item.strip() for item in args.path.split("/") if item.strip()]
    if args.include_self:
        payload["includeSelf"] = True
    return payload


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json_path:
        return json.loads(read_text_file(args.json_path))
    if args.stdin_json:
        return json.loads(sys.stdin.read())
    return {}


def dispatch(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    project = require_value(args.project, "project")
    node_id = require_value(args.node_id, "node-id")
    base_payload = {
        "project": project,
        "file": args.file or DEFAULT_FILE,
    }
    powan_kind = payload.get("powanKind") or payload.get("powan_kind") or ""
    if args.operation == "set-my-meaning":
        body = {**base_payload, "title": payload.get("title", ""), "body": payload.get("body", "")}
        if powan_kind:
            body["powanKind"] = powan_kind
        return request_json(args.api_base, "PATCH", f"/api/ai/powans/{node_id}", body)
    if args.operation == "create-child-powan":
        body = {
            **base_payload,
            "title": payload.get("title", ""),
            "body": payload.get("body", ""),
            "powanKind": powan_kind or "nerve",
            "codeLanguage": payload.get("codeLanguage") or payload.get("code_language") or "",
            "code": payload.get("code", ""),
        }
        return request_json(args.api_base, "POST", f"/api/ai/powans/{node_id}/children", body)
    if args.operation == "create-powan-tree":
        body = {
            **base_payload,
            "children": payload.get("children", []),
            "randomStyle": bool(payload.get("randomStyle") or payload.get("random_style") or False),
        }
        return request_json(args.api_base, "POST", f"/api/ai/powans/{node_id}/actions/tree", body)
    if args.operation == "delete-child-powan":
        body = {
            **base_payload,
            "title": payload.get("title", ""),
            "body": payload.get("body", ""),
            "deleteDescendants": bool(payload.get("deleteDescendants") or payload.get("delete_descendants") or False),
        }
        child_id = payload.get("childId") or payload.get("child_id") or ""
        if child_id:
            body["childId"] = child_id
        return request_json(args.api_base, "POST", f"/api/ai/powans/{node_id}/actions/delete-child", body)
    if args.operation == "restore-child-powan":
        body = {
            **base_payload,
            "title": payload.get("title", ""),
            "body": payload.get("body", ""),
        }
        child_id = payload.get("childId") or payload.get("child_id") or ""
        target_parent_id = payload.get("targetParentId") or payload.get("target_parent_id") or ""
        if child_id:
            body["childId"] = child_id
        if target_parent_id:
            body["targetParentId"] = target_parent_id
        return request_json(args.api_base, "POST", f"/api/ai/powans/{node_id}/actions/restore-child", body)
    if args.operation == "command-children":
        body = {
            **base_payload,
            "instruction": payload.get("instruction", ""),
            "instructions": payload.get("instructions", []),
            "includeMeaningTree": payload_flag(payload, "includeMeaningTree", "include_meaning_tree"),
            "continueAfterChildReplies": payload_flag(payload, "continueAfterChildReplies", "continue_after_child_replies"),
        }
        response = request_json(args.api_base, "POST", f"/api/ai/powans/{node_id}/actions/command-children", body)
        return summarize_command_children_response(response)
    if args.operation == "command-child-powan":
        body = {
            **base_payload,
            "instructions": [
                {
                    "title": payload.get("title", ""),
                    "body": payload.get("body", ""),
                    "childId": payload.get("childId") or payload.get("child_id") or None,
                    "instruction": payload.get("instruction", ""),
                }
            ],
            "includeMeaningTree": payload_flag(payload, "includeMeaningTree", "include_meaning_tree"),
            "continueAfterChildReplies": payload_flag(payload, "continueAfterChildReplies", "continue_after_child_replies"),
        }
        response = request_json(args.api_base, "POST", f"/api/ai/powans/{node_id}/actions/command-children", body)
        return summarize_command_children_response(response)
    if args.operation == "read-powan-codes":
        targets = payload.get("targets", [])
        if not isinstance(targets, list):
            raise ToolError("targets must be a list")
        direct_target = {
            key: payload.get(key)
            for key in ("title", "body", "path", "targetId", "childId")
            if payload.get(key)
        }
        if direct_target:
            targets = [*targets, direct_target]
        body = {
            **base_payload,
            "includeSelf": bool(payload.get("includeSelf") or payload.get("include_self") or False),
            "targets": targets,
        }
        return request_json(args.api_base, "POST", f"/api/ai/powans/{node_id}/actions/read-powan-codes", body)
    if args.operation == "write-my-code":
        body = {
            **base_payload,
            "code": payload.get("code", ""),
        }
        code_language = payload.get("codeLanguage") or payload.get("code_language") or ""
        if code_language:
            body["codeLanguage"] = code_language
        return request_json(args.api_base, "PATCH", f"/api/ai/powans/{node_id}", body)
    raise ToolError(f"Unknown operation: {args.operation}")


def request_json(api_base: str, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ToolError(f"{method} {url} failed: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise ToolError(f"{method} {url} failed: {exc}") from exc


def summarize_command_children_response(response: dict[str, Any]) -> dict[str, Any]:
    results = response.get("results") if isinstance(response.get("results"), list) else []
    sent_children = []
    skipped_children = []
    failed_children = []
    for item in results:
        if not isinstance(item, dict):
            continue
        child = {
            "childId": item.get("nodeId"),
            "title": item.get("meaning"),
            "status": item.get("status"),
        }
        status = str(item.get("status") or "")
        if status in {"accepted", "completed"}:
            sent_children.append(child)
        elif status == "skipped":
            skipped_children.append({**child, "skipReason": item.get("skipReason") or ""})
        else:
            failed_children.append({**child, "error": item.get("error") or ""})
    detached = bool(response.get("detached"))
    return {
        "status": "accepted" if detached else "completed",
        "detached": detached,
        "dispatchSessionId": response.get("dispatchSessionId") or "",
        "dispatchIntervalMs": response.get("dispatchIntervalMs"),
        "continueAfterChildReplies": bool(response.get("continueAfterChildReplies")),
        "parent": response.get("parent") or {},
        "sent": len(sent_children),
        "skipped": len(skipped_children),
        "failed": len(failed_children),
        "sentChildren": sent_children,
        "skippedChildren": skipped_children,
        "failedChildren": failed_children,
        "nextAction": "report_acceptance_and_stop",
        "message": "子ポワンへの一括指示を受け付けました。子の返答は後で親会話に戻ります。",
    }


def payload_flag(payload: dict[str, Any], *names: str) -> bool:
    for name in names:
        if name not in payload:
            continue
        value = payload.get(name)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)
    return False


def require_value(value: str, name: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ToolError(f"{name} is required")
    return clean


def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
