from __future__ import annotations

import random
import threading
from datetime import datetime, timezone
from math import cos, pi, sin
from typing import Any, Callable
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from powan_context import build_powan_context, summarize_powan
from powan_store import PowanStore


LogFn = Callable[[str, str, dict[str, Any] | None], None]
WORKSPACE_SIZE = 10000
WORKSPACE_ORIGIN_X = 5000
WORKSPACE_ORIGIN_Y = 5000
DEFAULT_NODE_WIDTH = 280
DEFAULT_NODE_HEIGHT = 160
INTERIOR_STAGE_WIDTH = 560
INTERIOR_STAGE_HEIGHT = 360
NESTED_DISPLAY_INSET = 28
DEFAULT_ARRANGE_SPACING = 1.0
DEFAULT_ARRANGE_SIZE = 1.0
POWAN_COLOR_PALETTE = [
    {"color": "#fff1b8", "accent": "#d8b500"},
    {"color": "#ffe1ef", "accent": "#ef6ea8"},
    {"color": "#dcf7ff", "accent": "#34a6cf"},
    {"color": "#e5f8c8", "accent": "#7db83f"},
    {"color": "#efe3ff", "accent": "#9b72df"},
    {"color": "#ffe7c7", "accent": "#ef9a3c"},
    {"color": "#dff7ec", "accent": "#42b883"},
    {"color": "#e2ecff", "accent": "#5f8fe8"},
]
POWAN_KIND_DEFAULT = "nerve"
POWAN_KIND_ALIASES = {
    "nerve": "nerve",
    "organ": "organ",
    "神経": "nerve",
    "臓器": "organ",
}
AI_WRITE_LOCK = threading.RLock()
MUTATING_ACTIONS = {
    "create-root-powan",
    "update-powan",
    "patch-powan",
    "create-child-powan",
    "split-powan",
    "create-powan-tree",
    "delete-child-powan",
    "restore-child-powan",
    "move-powan",
}


def normalize_powan_kind(value: Any) -> str:
    clean = str(value or "").strip()
    if not clean:
        return POWAN_KIND_DEFAULT
    normalized = POWAN_KIND_ALIASES.get(clean, clean)
    if normalized not in {"nerve", "organ"}:
        raise HTTPException(status_code=400, detail="powanKind must be nerve or organ")
    return normalized


class PowanPatch(BaseModel):
    project: str
    file: str = "project.powan"
    title: str | None = None
    body: str | None = None
    powanKind: str | None = None
    code: str | None = None
    codeLanguage: str | None = None
    layout: dict[str, Any] | None = None
    style: dict[str, Any] | None = None


class CreatePowanRequest(BaseModel):
    project: str
    file: str = "project.powan"
    title: str = ""
    body: str = ""
    powanKind: str | None = POWAN_KIND_DEFAULT
    code: str = ""
    codeLanguage: str | None = None
    randomStyle: bool = False
    layout: dict[str, Any] | None = None
    style: dict[str, Any] | None = None


class MovePowanRequest(BaseModel):
    project: str
    file: str = "project.powan"
    parentId: str | None = None
    layout: dict[str, Any] | None = None


class SplitChildRequest(BaseModel):
    title: str = ""
    body: str = ""
    powanKind: str | None = POWAN_KIND_DEFAULT
    code: str = ""
    codeLanguage: str | None = None
    layout: dict[str, Any] | None = None
    style: dict[str, Any] | None = None


class PowanTreeNode(BaseModel):
    title: str = ""
    body: str = ""
    powanKind: str | None = POWAN_KIND_DEFAULT
    code: str = ""
    codeLanguage: str | None = None
    layout: dict[str, Any] | None = None
    style: dict[str, Any] | None = None
    children: list["PowanTreeNode"] = Field(default_factory=list)


class SplitPowanRequest(BaseModel):
    project: str
    file: str = "project.powan"
    children: list[SplitChildRequest] = Field(default_factory=list)
    randomStyle: bool = False


class PowanTreeRequest(BaseModel):
    project: str
    file: str = "project.powan"
    children: list[PowanTreeNode] = Field(default_factory=list)
    randomStyle: bool = False


class DeleteChildPowanRequest(BaseModel):
    project: str
    file: str = "project.powan"
    title: str = ""
    body: str = ""
    childId: str | None = None
    deleteDescendants: bool = False


class RestoreChildPowanRequest(BaseModel):
    project: str
    file: str = "project.powan"
    title: str = ""
    body: str = ""
    childId: str | None = None
    targetParentId: str | None = None


class ReadPowanCodeTarget(BaseModel):
    title: str = ""
    body: str = ""
    path: list[str] = Field(default_factory=list)
    targetId: str | None = None
    childId: str | None = None


class ReadPowanCodesRequest(BaseModel):
    project: str
    file: str = "project.powan"
    includeSelf: bool = False
    targets: list[ReadPowanCodeTarget] = Field(default_factory=list)


class AiWorkspace:
    def __init__(self, store: PowanStore, default_file: str, log_event: LogFn) -> None:
        self.store = store
        self.work_root = store.work_root
        self.default_file = default_file
        self.log_event = log_event

    def safe_project_name(self, name: str) -> str:
        return self.store.safe_project_name(name)

    def safe_powan_name(self, name: str) -> str:
        return self.store.safe_powan_name(name or self.default_file)

    def project_root(self, project: str):
        return self.store.project_root(project)

    def powan_path(self, project: str, name: str | None = None):
        return self.store.powan_path(project, name or self.default_file)

    def ensure_project(self, project: str):
        return self.store.ensure_project(project)

    def load_doc(self, project: str, file: str | None = None) -> dict[str, Any]:
        return self.store.load_document(project, file or self.default_file)

    def save_doc(self, project: str, file: str, doc: dict[str, Any]) -> None:
        self.store.save_document(project, file, doc, write_export=True)

    def list_files(self, project: str) -> list[str]:
        return self.store.list_documents(project)

    def explorer(self, project: str, file: str | None = None) -> "AiPowanExplorer":
        name = self.safe_powan_name(file or self.default_file)
        return AiPowanExplorer(self, project=self.safe_project_name(project), file=name, doc=self.load_doc(project, name))

    def record_api_action(
        self,
        *,
        project: str,
        file: str,
        node_id: str | None,
        action: str,
        status: str,
        request_payload: dict[str, Any] | list[Any] | None = None,
        response_payload: dict[str, Any] | list[Any] | None = None,
        error_text: str = "",
    ) -> dict[str, Any] | None:
        try:
            return self.store.record_api_action(
                project,
                file,
                node_id,
                action,
                status,
                request_payload=request_payload,
                response_payload=response_payload,
                error_text=error_text,
            )
        except Exception as exc:
            self.log_event(
                "error",
                "ai-api-action-log-failed",
                {
                    "project": project,
                    "file": file,
                    "nodeId": node_id,
                    "action": action,
                    "status": status,
                    "error": repr(exc),
                    "request": request_payload or {},
                    "response": response_payload or {},
                },
            )
            return None


class AiPowanExplorer:
    def __init__(self, workspace: AiWorkspace, project: str, file: str, doc: dict[str, Any]) -> None:
        self.workspace = workspace
        self.project = project
        self.file = file
        self.doc = doc

    def save(self, action: str, details: dict[str, Any] | None = None) -> None:
        self.workspace.save_doc(self.project, self.file, self.doc)
        self.workspace.log_event("info", action, {"project": self.project, "file": self.file, **(details or {})})

    def nodes(self) -> list[dict[str, Any]]:
        nodes = self.doc.setdefault("nodes", [])
        if not isinstance(nodes, list):
            raise HTTPException(status_code=400, detail="Powan document nodes must be a list")
        return nodes

    def is_archived(self, node: dict[str, Any] | None) -> bool:
        return bool(node and node.get("archived"))

    def active_nodes(self) -> list[dict[str, Any]]:
        return [node for node in self.nodes() if not self.is_archived(node)]

    def node(self, node_id: str) -> dict[str, Any]:
        for node in self.nodes():
            if node.get("id") == node_id:
                return node
        raise HTTPException(status_code=404, detail="Powan not found")

    def node_or_none(self, node_id: str | None) -> dict[str, Any] | None:
        if not node_id:
            return None
        for node in self.nodes():
            if node.get("id") == node_id:
                return node
        return None

    def children_of(self, node_id: str | None) -> list[dict[str, Any]]:
        return [node for node in self.nodes() if not self.is_archived(node) and node.get("parent") == node_id]

    def children_of_any_state(self, node_id: str | None) -> list[dict[str, Any]]:
        return [node for node in self.nodes() if node.get("parent") == node_id]

    def archived_children_of(self, node_id: str | None) -> list[dict[str, Any]]:
        owner_id = str(node_id or "")
        return [
            node
            for node in self.nodes()
            if self.is_archived(node) and str(node.get("archivedParent") or "") == owner_id
        ]

    def is_descendant(self, candidate_id: str, ancestor_id: str) -> bool:
        current = self.node_or_none(candidate_id)
        seen: set[str] = set()
        while current and current.get("parent"):
            parent_id = current.get("parent")
            if parent_id == ancestor_id:
                return True
            if parent_id in seen:
                return False
            seen.add(parent_id)
            current = self.node_or_none(parent_id)
        return False

    def normalize_children(self) -> None:
        by_id = {node.get("id"): node for node in self.active_nodes()}
        for node in self.active_nodes():
            node_id = node.get("id")
            child_ids = [child.get("id") for child in self.active_nodes() if child.get("parent") == node_id]
            existing = [child_id for child_id in node.get("children", []) if child_id in by_id and by_id[child_id].get("parent") == node_id]
            node["children"] = list(dict.fromkeys([*existing, *child_ids]))

    def summarize_node(self, node: dict[str, Any]) -> dict[str, Any]:
        return summarize_powan(node)

    def number(self, value: Any, fallback: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return fallback
        return number

    def clamp_layout(self, layout: dict[str, Any]) -> dict[str, Any]:
        width = max(1, round(self.number(layout.get("width"), DEFAULT_NODE_WIDTH)))
        height = max(1, round(self.number(layout.get("height"), DEFAULT_NODE_HEIGHT)))
        max_x = max(0, WORKSPACE_SIZE - width)
        max_y = max(0, WORKSPACE_SIZE - height)
        x = round(self.number(layout.get("x"), WORKSPACE_ORIGIN_X - width / 2))
        y = round(self.number(layout.get("y"), WORKSPACE_ORIGIN_Y - height / 2))
        return {
            **layout,
            "x": min(max_x, max(0, x)),
            "y": min(max_y, max(0, y)),
            "width": width,
            "height": height,
        }

    def grid_rect(self, area: dict[str, float], size: dict[str, float], index: int, gap_x: int = 40, gap_y: int = 34) -> dict[str, int]:
        width = round(self.number(size.get("width"), DEFAULT_NODE_WIDTH))
        height = round(self.number(size.get("height"), DEFAULT_NODE_HEIGHT))
        area_width = max(width, self.number(area.get("width"), width))
        columns = max(1, int((area_width + gap_x) // max(1, width + gap_x)))
        column = index % columns
        row = index // columns
        return {
            "x": round(self.number(area.get("x"), WORKSPACE_ORIGIN_X) + column * (width + gap_x)),
            "y": round(self.number(area.get("y"), WORKSPACE_ORIGIN_Y) + row * (height + gap_y)),
            "width": width,
            "height": height,
        }

    def clamp_number(self, value: float, minimum: float, maximum: float) -> float:
        if maximum < minimum:
            return minimum
        return min(maximum, max(minimum, value))

    def root_layout_area(self) -> dict[str, int]:
        return {
            "x": WORKSPACE_ORIGIN_X - 2 * (DEFAULT_NODE_WIDTH + 48),
            "y": WORKSPACE_ORIGIN_Y - DEFAULT_NODE_HEIGHT // 2,
            "width": 4 * DEFAULT_NODE_WIDTH + 3 * 48,
            "height": 720,
        }

    def arrange_world_area(self) -> dict[str, int]:
        return {
            "x": round(WORKSPACE_ORIGIN_X - INTERIOR_STAGE_WIDTH / 2),
            "y": round(WORKSPACE_ORIGIN_Y - INTERIOR_STAGE_HEIGHT / 2),
            "width": INTERIOR_STAGE_WIDTH,
            "height": INTERIOR_STAGE_HEIGHT,
        }

    def parent_nested_area(self, parent: dict[str, Any]) -> dict[str, int]:
        layout = parent.get("layout") or {}
        width = self.number(layout.get("width"), DEFAULT_NODE_WIDTH)
        height = self.number(layout.get("height"), DEFAULT_NODE_HEIGHT)
        return {
            "x": NESTED_DISPLAY_INSET,
            "y": NESTED_DISPLAY_INSET,
            "width": round(max(56, width - NESTED_DISPLAY_INSET * 2)),
            "height": round(max(40, height - NESTED_DISPLAY_INSET * 2)),
        }

    def scaled_size(self, size: dict[str, float], scale: float = DEFAULT_ARRANGE_SIZE) -> dict[str, int]:
        factor = self.clamp_number(self.number(scale, DEFAULT_ARRANGE_SIZE), 0.5, 1.8)
        return {
            "width": round(size["width"] * factor),
            "height": round(size["height"] * factor),
        }

    def world_child_size(self, count: int, scale: float = DEFAULT_ARRANGE_SIZE) -> dict[str, int]:
        if count <= 1:
            size = {"width": 300, "height": 180}
        elif count <= 4:
            size = {"width": 220, "height": 132}
        elif count <= 9:
            size = {"width": 180, "height": 112}
        else:
            size = {"width": 150, "height": 96}
        return self.scaled_size(size, scale)

    def nested_child_size(self, count: int, scale: float = DEFAULT_ARRANGE_SIZE) -> dict[str, int]:
        if count <= 1:
            size = {"width": 150, "height": 58}
        elif count <= 4:
            size = {"width": 96, "height": 38}
        elif count <= 9:
            size = {"width": 72, "height": 30}
        else:
            size = {"width": 58, "height": 24}
        return self.scaled_size(size, scale)

    def arrange_anchors(self, count: int, spacing: float = DEFAULT_ARRANGE_SPACING) -> list[dict[str, float]]:
        if count <= 1:
            return [{"x": 0.5, "y": 0.5}]
        spacing_scale = self.clamp_number(self.number(spacing, DEFAULT_ARRANGE_SPACING), 0.5, 1.5)
        if count == 2:
            offset = self.clamp_number(0.18 * spacing_scale, 0.08, 0.46)
            return [{"x": 0.5 - offset, "y": 0.5}, {"x": 0.5 + offset, "y": 0.5}]
        radius = self.clamp_number((0.34 if count <= 4 else 0.38) * spacing_scale, 0.12, 0.48)
        return [
            {
                "x": 0.5 + cos(-pi / 2 + (pi * 2 * index) / count) * radius,
                "y": 0.5 + sin(-pi / 2 + (pi * 2 * index) / count) * radius,
            }
            for index in range(count)
        ]

    def rect_at_anchor(self, area: dict[str, float], size: dict[str, float], anchor: dict[str, float]) -> dict[str, int]:
        width = min(size["width"], max(8, self.number(area.get("width"), size["width"])))
        height = min(size["height"], max(6, self.number(area.get("height"), size["height"])))
        area_x = self.number(area.get("x"), 0)
        area_y = self.number(area.get("y"), 0)
        area_width = self.number(area.get("width"), width)
        area_height = self.number(area.get("height"), height)
        center_x = area_x + area_width * anchor["x"]
        center_y = area_y + area_height * anchor["y"]
        return {
            "x": round(self.clamp_number(center_x - width / 2, area_x, area_x + area_width - width)),
            "y": round(self.clamp_number(center_y - height / 2, area_y, area_y + area_height - height)),
            "width": round(width),
            "height": round(height),
        }

    def plan_arranged_children(self, parent: dict[str, Any], children: list[dict[str, Any]]) -> list[dict[str, Any]]:
        anchors = self.arrange_anchors(len(children))
        world_area = self.arrange_world_area()
        nested_area = self.parent_nested_area(parent)
        world_size = self.world_child_size(len(children))
        nested_size = self.nested_child_size(len(children))
        return [
            {
                "node": child,
                "worldLayout": self.rect_at_anchor(world_area, world_size, anchors[index]),
                "nestedLayout": self.rect_at_anchor(nested_area, nested_size, anchors[index]),
            }
            for index, child in enumerate(children)
        ]

    def arrange_children(self, parent_id: str, reason: str) -> None:
        parent = self.node(parent_id)
        children = self.children_of(parent_id)
        if not children:
            return
        for plan in self.plan_arranged_children(parent, children):
            child = plan["node"]
            child["layout"] = self.clamp_layout(plan["worldLayout"])
            nested_by_parent = child.setdefault("nestedLayoutByParent", {})
            nested_by_parent[parent_id] = plan["nestedLayout"]
        self.workspace.log_event(
            "debug",
            reason,
            {"project": self.project, "file": self.file, "parentId": parent_id, "childCount": len(children)},
        )

    def default_layout(self, index: int | None = None) -> dict[str, int]:
        # ルートポワンの初期位置。子ポワンは create_node 後に arrange_children で並べる。
        siblings = self.children_of(None)
        slot = len(siblings) if index is None else max(0, index)
        return self.grid_rect(
            self.root_layout_area(),
            {"width": DEFAULT_NODE_WIDTH, "height": DEFAULT_NODE_HEIGHT},
            slot,
            gap_x=48,
            gap_y=42,
        )

    def default_style(self, random_style: bool = False) -> dict[str, Any]:
        pair = random.choice(POWAN_COLOR_PALETTE) if random_style else {"color": "#ffffff", "accent": "#8ddcff"}
        return {
            "shape": "cloud",
            "color": pair["color"],
            "accent": pair["accent"],
            "glow": True,
            "blur": True,
            "motion": "soft",
        }

    def create_node(self, request: CreatePowanRequest, parent_id: str | None = None) -> dict[str, Any]:
        if parent_id is not None:
            self.node(parent_id)
        node = {
            "id": f"node-{uuid4().hex[:10]}",
            "title": request.title,
            "body": request.body,
            "powanKind": normalize_powan_kind(request.powanKind),
            "code": request.code,
            "parent": parent_id,
            "children": [],
            "style": {**self.default_style(request.randomStyle), **(request.style or {})},
        }
        # ルートはここで初期位置を持つ。子は親へ追加したあと兄弟まとめて整列する。
        if parent_id is None:
            sibling_index = len(self.children_of(None))
            node["layout"] = self.clamp_layout({**self.default_layout(sibling_index), **(request.layout or {})})
        elif request.layout:
            node["layout"] = self.clamp_layout(request.layout)
        if request.codeLanguage:
            node["codeLanguage"] = request.codeLanguage
        self.nodes().append(node)
        if parent_id:
            parent = self.node(parent_id)
            parent["children"] = list(dict.fromkeys([*(parent.get("children") or []), node["id"]]))
        self.normalize_children()
        if parent_id:
            self.arrange_children(parent_id, "ai-create-powan-arrange")
        self.save("ai-create-powan", {"nodeId": node["id"], "parentId": parent_id})
        return node

    def create_split_children(self, node_id: str, request: SplitPowanRequest) -> list[dict[str, Any]]:
        self.node(node_id)
        created: list[dict[str, Any]] = []
        for child in request.children:
            create_request = CreatePowanRequest(
                project=request.project,
                file=request.file,
                title=child.title,
                body=child.body,
                powanKind=child.powanKind,
                code=child.code,
                codeLanguage=child.codeLanguage,
                randomStyle=request.randomStyle,
                layout=child.layout,
                style=child.style,
            )
            created.append(self.create_node(create_request, parent_id=node_id))
        self.save("ai-split-powan", {"nodeId": node_id, "created": [node.get("id") for node in created]})
        return created

    def create_tree_children(self, node_id: str, request: PowanTreeRequest) -> list[dict[str, Any]]:
        self.node(node_id)
        created: list[dict[str, Any]] = []

        def create_branch(parent_id: str, branch: PowanTreeNode) -> dict[str, Any]:
            create_request = CreatePowanRequest(
                project=request.project,
                file=request.file,
                title=branch.title,
                body=branch.body,
                powanKind=branch.powanKind,
                code=branch.code,
                codeLanguage=branch.codeLanguage,
                randomStyle=request.randomStyle,
                layout=branch.layout,
                style=branch.style,
            )
            node = self.create_node(create_request, parent_id=parent_id)
            created.append(node)
            for child in branch.children:
                create_branch(str(node["id"]), child)
            return node

        roots = [create_branch(node_id, child) for child in request.children]
        self.normalize_children()
        self.save(
            "ai-create-powan-tree",
            {
                "nodeId": node_id,
                "rootIds": [node.get("id") for node in roots],
                "created": [node.get("id") for node in created],
            },
        )
        return created

    def descendants_of(self, node_id: str) -> list[dict[str, Any]]:
        descendants: list[dict[str, Any]] = []
        stack = list(self.children_of(node_id))
        while stack:
            current = stack.pop()
            descendants.append(current)
            stack.extend(self.children_of(str(current.get("id") or "")))
        return descendants

    def descendants_of_any_state(self, node_id: str) -> list[dict[str, Any]]:
        descendants: list[dict[str, Any]] = []
        stack = list(self.children_of_any_state(node_id))
        while stack:
            current = stack.pop()
            descendants.append(current)
            stack.extend(self.children_of_any_state(str(current.get("id") or "")))
        return descendants

    def matching_direct_children(self, node_id: str, request: DeleteChildPowanRequest) -> list[dict[str, Any]]:
        child_id = str(request.childId or "").strip()
        title = request.title.strip()
        body = request.body.strip()
        children = self.children_of(node_id)
        if child_id:
            return [child for child in children if str(child.get("id") or "") == child_id]
        if not title and not body:
            raise HTTPException(status_code=400, detail="title or body is required")
        matches = children
        if title:
            matches = [child for child in matches if str(child.get("title") or "").strip() == title]
        if body:
            matches = [child for child in matches if str(child.get("body") or "").strip() == body]
        return matches

    def matching_archived_children(self, node_id: str, request: RestoreChildPowanRequest) -> list[dict[str, Any]]:
        child_id = str(request.childId or "").strip()
        title = request.title.strip()
        body = request.body.strip()
        children = self.archived_children_of(node_id)
        if child_id:
            return [child for child in children if str(child.get("id") or "") == child_id]
        if not title and not body:
            raise HTTPException(status_code=400, detail="title or body is required")
        matches = children
        if title:
            matches = [child for child in matches if str(child.get("title") or "").strip() == title]
        if body:
            matches = [child for child in matches if str(child.get("body") or "").strip() == body]
        return matches

    def meaning_label(self, node: dict[str, Any]) -> str:
        return str(node.get("title") or node.get("body") or "名前のないポワン").strip() or "名前のないポワン"

    def matching_code_targets(
        self,
        candidates: list[dict[str, Any]],
        *,
        title: str = "",
        body: str = "",
        target_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clean_target_id = str(target_id or "").strip()
        clean_title = title.strip()
        clean_body = body.strip()
        if clean_target_id:
            return [node for node in candidates if str(node.get("id") or "") == clean_target_id]
        if not clean_title and not clean_body:
            raise HTTPException(status_code=400, detail="title or body is required")
        matches = candidates
        if clean_title:
            matches = [node for node in matches if str(node.get("title") or "").strip() == clean_title]
        if clean_body:
            matches = [node for node in matches if str(node.get("body") or "").strip() == clean_body]
        return matches

    def match_child_by_label(self, parent_id: str, label: str) -> dict[str, Any]:
        clean_label = label.strip()
        if not clean_label:
            raise HTTPException(status_code=400, detail="path item is required")
        matches = [
            child
            for child in self.children_of(parent_id)
            if clean_label
            in {
                str(child.get("title") or "").strip(),
                str(child.get("body") or "").strip(),
                self.meaning_label(child),
            }
        ]
        return self.one_code_target(
            matches,
            missing_detail=f"Powan path item not found: {clean_label}",
            multiple_detail=f"Multiple powans matched path item: {clean_label}",
        )

    def matches_code_label(self, node: dict[str, Any], label: str) -> bool:
        clean_label = label.strip()
        return clean_label in {
            str(node.get("title") or "").strip(),
            str(node.get("body") or "").strip(),
            self.meaning_label(node),
        }

    def match_global_path(self, path: list[str]) -> dict[str, Any]:
        labels = [str(label or "").strip() for label in path if str(label or "").strip()]
        if not labels:
            raise HTTPException(status_code=400, detail="path item is required")
        candidates = [node for node in self.active_nodes() if self.matches_code_label(node, labels[0])]
        for label in labels[1:]:
            next_candidates: list[dict[str, Any]] = []
            for candidate in candidates:
                next_candidates.extend(
                    child
                    for child in self.children_of(str(candidate.get("id") or ""))
                    if self.matches_code_label(child, label)
                )
            candidates = next_candidates
        return self.one_code_target(
            candidates,
            missing_detail=f"Powan code path not found: {' / '.join(labels)}",
            multiple_detail=f"Multiple powan code paths matched: {' / '.join(labels)}",
        )

    def one_code_target(self, matches: list[dict[str, Any]], *, missing_detail: str, multiple_detail: str) -> dict[str, Any]:
        if not matches:
            raise HTTPException(status_code=404, detail=missing_detail)
        if len(matches) > 1:
            raise HTTPException(status_code=409, detail=multiple_detail)
        return matches[0]

    def code_path_from(self, ancestor_id: str, node: dict[str, Any]) -> list[str]:
        path: list[str] = []
        current: dict[str, Any] | None = node
        while current:
            path.append(self.meaning_label(current))
            current_id = str(current.get("id") or "")
            if current_id == ancestor_id:
                break
            current = self.node_or_none(current.get("parent"))
        path.reverse()
        return path

    def code_payload(self, node: dict[str, Any], *, root_id: str) -> dict[str, Any]:
        code = str(node.get("code") or "")
        return {
            "path": self.code_path_from(root_id, node),
            "meaning": str(node.get("body") or node.get("title") or "").strip(),
            "title": node.get("title") or "",
            "body": node.get("body") or "",
            "powanKind": normalize_powan_kind(node.get("powanKind")),
            "codeLanguage": node.get("codeLanguage") or "",
            "hasCode": bool(code.strip()),
            "code": code,
        }

    def resolve_code_target(self, node_id: str, target: ReadPowanCodeTarget) -> dict[str, Any]:
        if target.path:
            return self.match_global_path(target.path)
        matches = self.matching_code_targets(
            self.active_nodes(),
            title=target.title,
            body=target.body,
            target_id=target.targetId or target.childId,
        )
        return self.one_code_target(
            matches,
            missing_detail="Powan code target not found",
            multiple_detail="Multiple powan code targets matched",
        )

    def read_powan_codes(self, node_id: str, request: ReadPowanCodesRequest) -> dict[str, Any]:
        self.node(node_id)
        codes: list[dict[str, Any]] = []
        seen: set[str] = set()
        if request.includeSelf:
            node = self.node(node_id)
            seen.add(str(node.get("id") or ""))
            codes.append(self.code_payload(node, root_id=node_id))
        for target in request.targets:
            node = self.resolve_code_target(node_id, target)
            node_key = str(node.get("id") or "")
            if node_key in seen:
                continue
            seen.add(node_key)
            codes.append(self.code_payload(node, root_id=node_id))
        return {"codes": codes}

    def delete_child(self, node_id: str, request: DeleteChildPowanRequest) -> dict[str, Any]:
        parent = self.node(node_id)
        matches = self.matching_direct_children(node_id, request)
        if not matches:
            raise HTTPException(status_code=404, detail="Child powan not found")
        if len(matches) > 1:
            raise HTTPException(status_code=409, detail="Multiple child powans matched")
        child = matches[0]
        child_id = str(child.get("id") or "")
        descendant_nodes = self.descendants_of_any_state(child_id)
        if descendant_nodes and not request.deleteDescendants:
            raise HTTPException(status_code=400, detail="Child powan has descendants")
        archive_ids = {child_id}
        if request.deleteDescendants:
            archive_ids.update(str(node.get("id") or "") for node in descendant_nodes)
        archived_nodes = [node for node in self.nodes() if str(node.get("id") or "") in archive_ids]
        archived_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for archived_node in archived_nodes:
            original_parent = archived_node.get("parent")
            archived_node["archived"] = True
            archived_node["archivedAt"] = archived_at
            archived_node["archivedParent"] = original_parent
        child["parent"] = None
        parent["children"] = [item for item in parent.get("children", []) if str(item) != child_id]
        self.normalize_children()
        self.save("ai-archive-child-powan", {"nodeId": node_id, "archived": sorted(archive_ids)})
        return {
            "parent": self.summarize_node(self.node(node_id)),
            "archived": [self.summarize_node(node) for node in archived_nodes],
            "deleted": [],
        }

    def restore_archived_child(self, node_id: str, request: RestoreChildPowanRequest) -> dict[str, Any]:
        restore_parent_id = request.targetParentId or node_id
        parent = self.node(restore_parent_id)
        matches = self.matching_archived_children(node_id, request)
        if not matches:
            raise HTTPException(status_code=404, detail="Archived child powan not found")
        if len(matches) > 1:
            raise HTTPException(status_code=409, detail="Multiple archived child powans matched")
        child = matches[0]
        child_id = str(child.get("id") or "")
        if restore_parent_id == child_id or self.is_descendant(restore_parent_id, child_id):
            raise HTTPException(status_code=400, detail="Cannot restore powan into itself or its descendant")
        restore_ids = {child_id}
        restore_ids.update(str(node.get("id") or "") for node in self.descendants_of_any_state(child_id))
        restored_nodes = [node for node in self.nodes() if str(node.get("id") or "") in restore_ids]
        child["parent"] = restore_parent_id
        # 復元先での位置はフロントの powanPlacement が読み込み時に補完する。
        for restored_node in restored_nodes:
            restored_node.pop("archived", None)
            restored_node.pop("archivedAt", None)
            restored_node.pop("archivedParent", None)
        parent["children"] = list(dict.fromkeys([*(parent.get("children") or []), child_id]))
        self.normalize_children()
        self.save(
            "ai-restore-child-powan",
            {"nodeId": node_id, "targetParentId": restore_parent_id, "restored": sorted(restore_ids)},
        )
        return {
            "parent": self.summarize_node(self.node(restore_parent_id)),
            "restored": [self.summarize_node(node) for node in restored_nodes],
        }

    def update_node(self, node_id: str, patch: PowanPatch) -> dict[str, Any]:
        node = self.node(node_id)
        for key in ("title", "body", "code", "codeLanguage"):
            value = getattr(patch, key)
            if value is not None:
                node[key] = value
        if patch.powanKind is not None:
            node["powanKind"] = normalize_powan_kind(patch.powanKind)
        if patch.layout is not None:
            node["layout"] = self.clamp_layout({**(node.get("layout") or {}), **patch.layout})
        if patch.style is not None:
            node["style"] = {**(node.get("style") or {}), **patch.style}
        self.normalize_children()
        self.save("ai-update-powan", {"nodeId": node_id})
        return node

    def move_node(self, node_id: str, request: MovePowanRequest) -> dict[str, Any]:
        node = self.node(node_id)
        parent_id = request.parentId
        if parent_id == node_id or (parent_id and self.is_descendant(parent_id, node_id)):
            raise HTTPException(status_code=400, detail="Cannot move powan into itself or its descendant")
        if parent_id:
            self.node(parent_id)
        old_parent_id = node.get("parent")
        node["parent"] = parent_id
        if request.layout is not None:
            node["layout"] = self.clamp_layout({**(node.get("layout") or {}), **request.layout})
        self.normalize_children()
        self.save("ai-move-powan", {"nodeId": node_id, "oldParentId": old_parent_id, "parentId": parent_id})
        return node

    def context(self, node_id: str) -> dict[str, Any]:
        self.node(node_id)
        return build_powan_context(
            project=self.project,
            document_name=self.file,
            document=self.doc,
            node_id=node_id,
        )


def create_ai_router(store: PowanStore, default_file: str, log_event: LogFn) -> APIRouter:
    router = APIRouter(prefix="/api/ai", tags=["ai"])
    workspace = AiWorkspace(store, default_file, log_event)

    def request_payload(request: BaseModel) -> dict[str, Any]:
        if hasattr(request, "model_dump"):
            return request.model_dump(mode="json")
        return request.dict()

    def action_node_id(default_node_id: str | None, response: dict[str, Any]) -> str | None:
        if default_node_id:
            return default_node_id
        powan = response.get("powan") if isinstance(response, dict) else None
        if isinstance(powan, dict):
            return str(powan.get("id") or "") or None
        return None

    def run_logged_action(
        action: str,
        node_id: str | None,
        request: BaseModel,
        handler: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        payload = request_payload(request)
        project = str(payload.get("project") or "")
        file = str(payload.get("file") or default_file)
        try:
            if action in MUTATING_ACTIONS:
                workspace.log_event(
                    "trace",
                    "ai-api-write-lock-wait",
                    {"project": project, "file": file, "nodeId": node_id, "action": action},
                )
                with AI_WRITE_LOCK:
                    workspace.log_event(
                        "trace",
                        "ai-api-write-lock-enter",
                        {"project": project, "file": file, "nodeId": node_id, "action": action},
                    )
                    response = handler()
                    workspace.log_event(
                        "trace",
                        "ai-api-write-lock-exit",
                        {"project": project, "file": file, "nodeId": action_node_id(node_id, response), "action": action},
                    )
            else:
                response = handler()
        except HTTPException as exc:
            workspace.record_api_action(
                project=project,
                file=file,
                node_id=node_id,
                action=action,
                status="failed",
                request_payload=payload,
                response_payload={},
                error_text=str(exc.detail),
            )
            raise
        except Exception as exc:
            workspace.record_api_action(
                project=project,
                file=file,
                node_id=node_id,
                action=action,
                status="failed",
                request_payload=payload,
                response_payload={},
                error_text=repr(exc),
            )
            raise
        workspace.record_api_action(
            project=project,
            file=file,
            node_id=action_node_id(node_id, response),
            action=action,
            status="completed",
            request_payload=payload,
            response_payload=response,
        )
        return response

    @router.get("")
    def ai_entry() -> dict[str, Any]:
        return {
            "name": "ABC Canvas AI API",
            "capabilities": ["read", "context", "create", "update", "move", "split", "tree", "archive", "restore", "code-read", "command-children", "action-logs"],
            "encoding": "utf-8-json-body",
            "note": "Send Japanese text in JSON request bodies, not as shell command arguments.",
            "endpoints": {
                "projects": "/api/ai/projects",
                "project": "/api/ai/project?project={project}",
                "powans": "/api/ai/powans?project={project}&file=project.powan",
                "powan": "/api/ai/powans/{id}?project={project}&file=project.powan",
                "context": "/api/ai/powans/{id}/context?project={project}&file=project.powan",
                "createRoot": "POST /api/ai/powans",
                "createChild": "POST /api/ai/powans/{id}/children",
                "createTree": "POST /api/ai/powans/{id}/actions/tree",
                "archiveChild": "POST /api/ai/powans/{id}/actions/delete-child",
                "restoreChild": "POST /api/ai/powans/{id}/actions/restore-child",
                "readPowanCodes": "POST /api/ai/powans/{id}/actions/read-powan-codes",
                "update": "PATCH /api/ai/powans/{id}",
                "move": "POST /api/ai/powans/{id}/move",
                "split": "POST /api/ai/powans/{id}/actions/split",
                "actionLogs": "GET /api/ai/action-logs?project={project}&file=project.powan&nodeId={id}",
            },
        }

    @router.get("/projects")
    def ai_projects() -> dict[str, Any]:
        projects = [
            {"name": path.name, "path": str(path)}
            for path in sorted(workspace.work_root.iterdir(), key=lambda item: item.name)
            if path.is_dir()
        ]
        return {"projects": projects}

    @router.get("/project")
    def ai_project(project: str) -> dict[str, Any]:
        root = workspace.ensure_project(project)
        files = workspace.list_files(project)
        return {"project": workspace.safe_project_name(project), "root": str(root), "files": files}

    @router.get("/powans")
    def ai_powans(project: str, file: str = Query(default_file)) -> dict[str, Any]:
        explorer = workspace.explorer(project, file)
        explorer.normalize_children()
        return {
            "project": explorer.project,
            "file": explorer.file,
            "powans": [explorer.summarize_node(node) for node in explorer.active_nodes()],
        }

    @router.get("/powans/{node_id}")
    def ai_powan(node_id: str, project: str, file: str = Query(default_file)) -> dict[str, Any]:
        explorer = workspace.explorer(project, file)
        return {"project": explorer.project, "file": explorer.file, "powan": explorer.summarize_node(explorer.node(node_id))}

    @router.get("/powans/{node_id}/context")
    def ai_powan_context(node_id: str, project: str, file: str = Query(default_file)) -> dict[str, Any]:
        return workspace.explorer(project, file).context(node_id)

    @router.post("/powans")
    def ai_create_root(request: CreatePowanRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            node = explorer.create_node(request, parent_id=None)
            return {"project": explorer.project, "file": explorer.file, "powan": explorer.summarize_node(node)}

        return run_logged_action("create-root-powan", None, request, handler)

    @router.post("/powans/{node_id}")
    def ai_update_powan(node_id: str, request: PowanPatch) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            node = explorer.update_node(node_id, request)
            return {"project": explorer.project, "file": explorer.file, "powan": explorer.summarize_node(node)}

        return run_logged_action("update-powan", node_id, request, handler)

    @router.patch("/powans/{node_id}")
    def ai_patch_powan(node_id: str, request: PowanPatch) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            node = explorer.update_node(node_id, request)
            return {"project": explorer.project, "file": explorer.file, "powan": explorer.summarize_node(node)}

        return run_logged_action("patch-powan", node_id, request, handler)

    @router.post("/powans/{node_id}/children")
    def ai_create_child(node_id: str, request: CreatePowanRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            node = explorer.create_node(request, parent_id=node_id)
            return {"project": explorer.project, "file": explorer.file, "powan": explorer.summarize_node(node)}

        return run_logged_action("create-child-powan", node_id, request, handler)

    @router.post("/powans/{node_id}/actions/split")
    def ai_split_powan(node_id: str, request: SplitPowanRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            if not request.children:
                raise HTTPException(status_code=400, detail="children is required")
            explorer = workspace.explorer(request.project, request.file)
            created = explorer.create_split_children(node_id, request)
            return {
                "project": explorer.project,
                "file": explorer.file,
                "parent": explorer.summarize_node(explorer.node(node_id)),
                "children": [explorer.summarize_node(node) for node in created],
            }

        return run_logged_action("split-powan", node_id, request, handler)

    @router.post("/powans/{node_id}/actions/tree")
    def ai_create_powan_tree(node_id: str, request: PowanTreeRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            if not request.children:
                raise HTTPException(status_code=400, detail="children is required")
            explorer = workspace.explorer(request.project, request.file)
            created = explorer.create_tree_children(node_id, request)
            return {
                "project": explorer.project,
                "file": explorer.file,
                "parent": explorer.summarize_node(explorer.node(node_id)),
                "created": [explorer.summarize_node(node) for node in created],
            }

        return run_logged_action("create-powan-tree", node_id, request, handler)

    @router.post("/powans/{node_id}/actions/delete-child")
    def ai_delete_child_powan(node_id: str, request: DeleteChildPowanRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            result = explorer.delete_child(node_id, request)
            return {"project": explorer.project, "file": explorer.file, **result}

        return run_logged_action("delete-child-powan", node_id, request, handler)

    @router.post("/powans/{node_id}/actions/restore-child")
    def ai_restore_child_powan(node_id: str, request: RestoreChildPowanRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            result = explorer.restore_archived_child(node_id, request)
            return {"project": explorer.project, "file": explorer.file, **result}

        return run_logged_action("restore-child-powan", node_id, request, handler)

    @router.post("/powans/{node_id}/actions/read-powan-codes")
    def ai_read_powan_codes(node_id: str, request: ReadPowanCodesRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            result = explorer.read_powan_codes(node_id, request)
            return {"project": explorer.project, "file": explorer.file, **result}

        return run_logged_action("read-powan-codes", node_id, request, handler)

    @router.post("/powans/{node_id}/move")
    def ai_move_powan(node_id: str, request: MovePowanRequest) -> dict[str, Any]:
        def handler() -> dict[str, Any]:
            explorer = workspace.explorer(request.project, request.file)
            node = explorer.move_node(node_id, request)
            return {"project": explorer.project, "file": explorer.file, "powan": explorer.summarize_node(node)}

        return run_logged_action("move-powan", node_id, request, handler)

    @router.get("/action-logs")
    def ai_action_logs(
        project: str,
        file: str = Query(default_file),
        nodeId: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return store.list_api_action_logs(project, file, powan_id=nodeId, limit=limit)

    return router
