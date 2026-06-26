from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_api import create_ai_router
from codex_bridge import CodexPowanBridge
from powan_store import PowanStore


APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
POWAN_WORK_ROOT = APP_ROOT / "powan_work"
SETTING_ROOT = APP_ROOT / "setting"
DEFAULT_SOUND_ROOT = SETTING_ROOT / "sound"
SETTINGS_PATH = SETTING_ROOT / "settings.json"
LOG_ROOT = APP_ROOT / "logs"
CLIENT_LOG_PATH = LOG_ROOT / "abc_canvas.log"
RESTART_LOG_PATH = LOG_ROOT / "abc_canvas_restart.log"
START_SCRIPT_PATH = APP_ROOT / "start_abc_canvas.bat"
DEFAULT_FILE = "project.powan"
SOUND_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
INLINE_IMAGE_MAX_BYTES = 25 * 1024 * 1024
IMAGE_MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
DEFAULT_CONVERSATION_SOUND_VOLUME = 0.55
DEFAULT_INPUT_SOUND_VOLUME = 0.55
DEFAULT_AUTO_SUMMARY_ENABLED = True
DEFAULT_AUTO_SUMMARY_TURNS = 50
MIN_AUTO_SUMMARY_TURNS = 2
MAX_AUTO_SUMMARY_TURNS = 500
DEFAULT_CODEX_SANDBOX = "danger-full-access"
CODEX_SANDBOXES = {"read-only", "workspace-write", "danger-full-access"}
DEFAULT_ARRANGE_SPACING = 1.0
DEFAULT_ARRANGE_SIZE = 1.0
MIN_ARRANGE_SPACING = 0.3
MAX_ARRANGE_SPACING = 3.0
MIN_ARRANGE_SIZE = 0.3
MAX_ARRANGE_SIZE = 2.5
WORKSPACE_SIZE = 10000
WORKSPACE_ORIGIN_X = 5000
WORKSPACE_ORIGIN_Y = 5000
DEFAULT_NODE_WIDTH = 280
DEFAULT_NODE_HEIGHT = 160
CONSOLE_TEXT_PREVIEW_CHARS = 30
LOG_LEVEL_NAMES = ("trace", "debug", "info", "warn", "error", "fatal")
DEFAULT_CONSOLE_LOG_LEVELS = ("info", "warn", "error")
POWAN_WORK_EVENT_LIMIT = 500
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

POWAN_WORK_ROOT.mkdir(parents=True, exist_ok=True)
SETTING_ROOT.mkdir(parents=True, exist_ok=True)
DEFAULT_SOUND_ROOT.mkdir(parents=True, exist_ok=True)
LOG_ROOT.mkdir(parents=True, exist_ok=True)

POWAN_WORK_EVENTS: list[dict[str, Any]] = []
POWAN_WORK_EVENT_SEQUENCE = 0
POWAN_WORK_EVENT_LOCK = threading.Lock()


def reset_logs() -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    for path in LOG_ROOT.glob("*.log"):
        if path.is_file() and path != RESTART_LOG_PATH:
            path.unlink()
    CLIENT_LOG_PATH.write_text("", encoding="utf-8")


def write_log_entries(entries: list[dict[str, Any]]) -> int:
    if not entries:
        return 0
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    server_time = datetime.now().isoformat(timespec="milliseconds")
    lines = [
        json.dumps(
            {
                "serverTime": server_time,
                "entry": entry,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for entry in entries
    ]
    with CLIENT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return len(lines)


def compact_console_text(value: Any, limit: int = CONSOLE_TEXT_PREVIEW_CHARS) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def console_preview_text(details: dict[str, Any] | None) -> str:
    if not details:
        return ""
    for key in ("textPreview", "instructionPreview", "error", "detail"):
        value = details.get(key)
        if value:
            return compact_console_text(value)
    return ""


def normalize_console_log_levels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return list(DEFAULT_CONSOLE_LOG_LEVELS)
    values = {str(item).lower() for item in value}
    levels = [level for level in LOG_LEVEL_NAMES if level in values]
    return levels or list(DEFAULT_CONSOLE_LOG_LEVELS)


def current_console_log_levels() -> list[str]:
    if not SETTINGS_PATH.exists():
        return list(DEFAULT_CONSOLE_LOG_LEVELS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(DEFAULT_CONSOLE_LOG_LEVELS)
    return normalize_console_log_levels(data.get("consoleLogLevels"))


def should_print_server_event(level: str, details: dict[str, Any] | None) -> bool:
    return level.lower() in set(current_console_log_levels())


def print_server_event(level: str, action: str, details: dict[str, Any] | None) -> None:
    message = str((details or {}).get("message") or "")
    preview = console_preview_text(details)
    suffix = f' "{preview}"' if preview else ""
    print(f"{datetime.now().isoformat(timespec='seconds')} {level.upper()} {action} {message}{suffix}", flush=True)


def log_server_event(level: str, action: str, details: dict[str, Any] | None = None) -> None:
    write_log_entries(
        [
            {
                "level": level,
                "action": action,
                "source": "server",
                "pid": os.getpid(),
                **(details or {}),
            }
        ]
    )
    if should_print_server_event(level, details):
        print_server_event(level, action, details)


reset_logs()
log_server_event("info", "server-startup", {"appRoot": str(APP_ROOT)})


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict[str, Any]):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


def no_cache_file(path: Path) -> FileResponse:
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


app = FastAPI(title="ABC Canvas")
app.mount("/static", NoCacheStaticFiles(directory=STATIC_ROOT), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    log_server_event(
        "warn",
        "request-validation-error",
        {
            "method": request.method,
            "path": request.url.path,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


class AbcDocument(BaseModel):
    version: int = 1
    canvas: dict[str, Any] = Field(default_factory=dict)
    nodes: list[dict[str, Any]] = Field(default_factory=list)


class ProjectCreateRequest(BaseModel):
    name: str


class ClientLogBatch(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


class ShutdownRequest(BaseModel):
    reason: str = "frontend"


class RestartRequest(BaseModel):
    reason: str = "frontend"
    visibleConsole: bool | None = None


class SoundFolderRequest(BaseModel):
    soundRoot: str


class ConversationSoundRequest(BaseModel):
    conversationSound: str = ""


class ConversationSoundVolumeRequest(BaseModel):
    conversationSoundVolume: float


class InputSoundRequest(BaseModel):
    inputSound: str = ""


class InputSoundVolumeRequest(BaseModel):
    inputSoundVolume: float


class ConversationAutoSummaryRequest(BaseModel):
    enabled: bool
    turns: int


class CodexSandboxRequest(BaseModel):
    codexSandbox: str


class ArrangeSettingsRequest(BaseModel):
    arrangeSpacing: float
    arrangeSize: float
    arrangeResizeParents: bool = True
    arrangeRecursive: bool = True
    arrangeChildSpacing: float | None = None
    arrangeChildSize: float | None = None
    arrangeNestedChildSize: float | None = None
    arrangeWorldParentSpacing: float | None = None
    arrangeWorldParentSize: float | None = None
    nestedLayerScale: float | None = None


class ConsoleLogSettingsRequest(BaseModel):
    consoleLogLevels: list[str] = Field(default_factory=list)


class RestartVisibleConsoleSettingsRequest(BaseModel):
    restartVisibleConsole: bool = False


class ConversationMessageRequest(BaseModel):
    role: str = "user"
    text: str


class PowanCodexRequest(BaseModel):
    text: str
    includeMeaningTree: bool = False
    includeDirectChildCode: bool = False
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class ChildCommandRequest(BaseModel):
    title: str = ""
    body: str = ""
    childId: str | None = None
    instruction: str = ""


class CommandChildrenRequest(BaseModel):
    project: str
    file: str = DEFAULT_FILE
    instruction: str = ""
    instructions: list[ChildCommandRequest] = Field(default_factory=list)
    includeMeaningTree: bool = False
    continueOnError: bool = True
    parallel: bool = True
    maxParallel: int = 3
    staggerMs: int = 1000


def base_model_payload(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def record_api_action_safely(
    *,
    project: str,
    file: str,
    node_id: str | None,
    action: str,
    status: str,
    request_payload: dict[str, Any] | list[Any] | None = None,
    response_payload: dict[str, Any] | list[Any] | None = None,
    error_text: str = "",
) -> None:
    try:
        STORE.record_api_action(
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
        log_server_event(
            "error",
            "powan-api-action-log-failed",
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


def conversation_attachment_lines(attachments: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for attachment in attachments[:20]:
        if not isinstance(attachment, dict):
            continue
        kind = str(attachment.get("kind") or "file")
        name = str(attachment.get("name") or attachment.get("host") or attachment.get("url") or "attachment")
        path = str(attachment.get("path") or "")
        url = str(attachment.get("url") or "")
        if path:
            lines.append(f"- {kind}: {name}\n  path: {path}")
        elif url:
            lines.append(f"- {kind}: {name}\n  url: {url}")
        else:
            lines.append(f"- {kind}: {name}\n  path: （ブラウザから取得できない）")
    return lines


def conversation_record_text(text: str, attachments: list[dict[str, Any]]) -> str:
    parts = []
    clean_text = text.strip()
    if clean_text:
        parts.append(clean_text)
    attachment_lines = conversation_attachment_lines(attachments)
    if attachment_lines:
        parts.append("添付:\n" + "\n".join(attachment_lines))
    return "\n\n".join(parts) or "添付を渡す"


def windows_process_summary(pid: int) -> dict[str, Any] | None:
    if os.name != "nt":
        return None
    script = (
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
        "if ($p) { "
        "[pscustomobject]@{ProcessId=$p.ProcessId;ParentProcessId=$p.ParentProcessId;Name=$p.Name;CommandLine=$p.CommandLine} | ConvertTo-Json -Compress "
        "}"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def should_shutdown_parent(pid: int) -> bool:
    info = windows_process_summary(pid)
    if not info:
        return False
    name = str(info.get("Name") or "").lower()
    command = str(info.get("CommandLine") or "").lower()
    return "python" in name and "uvicorn" in command and "app:app" in command and ("8790" in command or "abc_canvas" in command)


def should_shutdown_batch_shell(pid: int) -> bool:
    info = windows_process_summary(pid)
    if not info:
        return False
    name = str(info.get("Name") or "").lower()
    command = str(info.get("CommandLine") or "").lower()
    return name == "cmd.exe" and "start_abc_canvas.bat" in command


def shutdown_target_pids() -> list[int]:
    pids = [os.getpid()]
    parent_pid = os.getppid()
    if parent_pid and parent_pid not in pids and should_shutdown_parent(parent_pid):
        pids.append(parent_pid)
        parent_info = windows_process_summary(parent_pid) or {}
        grandparent_pid = int(parent_info.get("ParentProcessId") or 0)
        if grandparent_pid and grandparent_pid not in pids and should_shutdown_batch_shell(grandparent_pid):
            pids.append(grandparent_pid)
    return pids


def shutdown_later(pids: list[int]) -> None:
    time.sleep(0.35)
    log_server_event("info", "shutdown-execute", {"targetPids": pids})
    if os.name == "nt":
        args = ["taskkill"]
        for pid in pids:
            args.extend(["/PID", str(pid)])
        args.extend(["/T", "/F"])
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
    os._exit(0)


def restart_helper_code() -> str:
    return r"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

app_root = Path(os.environ["ABC_CANVAS_RESTART_ROOT"])
python_exe = os.environ.get("ABC_CANVAS_RESTART_PYTHON") or sys.executable
log_path = os.environ.get("ABC_CANVAS_RESTART_LOG")
start_script = Path(os.environ.get("ABC_CANVAS_RESTART_START_SCRIPT") or "")
visible_console = os.environ.get("ABC_CANVAS_RESTART_VISIBLE_CONSOLE") == "1"


def helper_log(action, **details):
    if not log_path:
        return
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "action": action,
        **details,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


try:
    helper_log("restart-helper-start", appRoot=str(app_root), python=python_exe, visibleConsole=visible_console)
    deadline = time.time() + 12
    port_busy = True
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        try:
            port_busy = sock.connect_ex(("127.0.0.1", 8790)) == 0
        finally:
            sock.close()
        if not port_busy:
            helper_log("restart-helper-port-free")
            break
        time.sleep(0.25)
    if port_busy:
        helper_log("restart-helper-port-wait-timeout")
    time.sleep(0.25)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if visible_console and os.name == "nt" and start_script.exists():
        process = subprocess.Popen(
            [str(start_script)],
            cwd=str(app_root),
            env=env,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        helper_log("restart-helper-visible-cmd-started", pid=process.pid, startScript=str(start_script))
    else:
        flags = 0
        if os.name == "nt":
            flags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            )
        process = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8790", "--no-access-log"],
            cwd=str(app_root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        helper_log("restart-helper-hidden-uvicorn-started", pid=process.pid)
except Exception as exc:
    helper_log("restart-helper-error", error=repr(exc))
    raise
"""


def launch_restart_helper(visible_console: bool = False) -> int | None:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["ABC_CANVAS_RESTART_ROOT"] = str(APP_ROOT)
    env["ABC_CANVAS_RESTART_PYTHON"] = sys.executable
    env["ABC_CANVAS_RESTART_LOG"] = str(RESTART_LOG_PATH)
    env["ABC_CANVAS_RESTART_START_SCRIPT"] = str(START_SCRIPT_PATH)
    env["ABC_CANVAS_RESTART_VISIBLE_CONSOLE"] = "1" if visible_console else "0"
    flags = 0
    if os.name == "nt":
        flags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    log_server_event(
        "info",
        "restart-helper-launch",
        {
            "python": sys.executable,
            "appRoot": str(APP_ROOT),
            "restartLog": str(RESTART_LOG_PATH),
            "visibleConsole": bool(visible_console),
            "startScript": str(START_SCRIPT_PATH),
        },
    )
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", restart_helper_code()],
            cwd=str(APP_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except OSError as exc:
        log_server_event(
            "error",
            "restart-helper-launch-failed",
            {"error": str(exc), "restartLog": str(RESTART_LOG_PATH), "visibleConsole": bool(visible_console)},
        )
        return None
    log_server_event(
        "info",
        "restart-helper-launched",
        {"helperPid": process.pid, "restartLog": str(RESTART_LOG_PATH), "visibleConsole": bool(visible_console)},
    )
    return process.pid


def kill_pids_later(pids: list[int], *, tree: bool) -> None:
    time.sleep(0.35)
    if os.name == "nt":
        args = ["taskkill"]
        for pid in pids:
            args.extend(["/PID", str(pid)])
        if tree:
            args.append("/T")
        args.append("/F")
        log_server_event("info", "restart-kill-targets", {"targetPids": pids, "tree": tree})
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
    os._exit(0)


def restart_later(pids: list[int], visible_console: bool = False) -> None:
    helper_pid = launch_restart_helper(visible_console=visible_console)
    if helper_pid is None:
        log_server_event(
            "error",
            "restart-aborted",
            {"reason": "helper launch failed", "targetPids": pids, "visibleConsole": bool(visible_console)},
        )
        return
    log_server_event(
        "info",
        "restart-kill-old-server",
        {"helperPid": helper_pid, "targetPids": pids, "visibleConsole": bool(visible_console)},
    )
    kill_pids_later(pids, tree=False)


def safe_project_name(name: str) -> str:
    candidate = name.strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="Project name is required")
    if Path(candidate).name != candidate or any(part in candidate for part in ("/", "\\")):
        raise HTTPException(status_code=400, detail="Invalid project name")
    invalid_chars = set('<>:"|?*')
    if any(char in invalid_chars or ord(char) < 32 for char in candidate):
        raise HTTPException(status_code=400, detail="Invalid project name")
    if candidate in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid project name")
    return candidate


def safe_powan_name(name: str) -> str:
    safe_name = Path(name).name
    if not safe_name.endswith(".powan"):
        safe_name += ".powan"
    if safe_name in {".powan", "..powan"}:
        raise HTTPException(status_code=400, detail="Invalid powan file name")
    return safe_name


def project_root(name: str) -> Path:
    safe_name = safe_project_name(name)
    path = (POWAN_WORK_ROOT / safe_name).resolve()
    if POWAN_WORK_ROOT.resolve() not in path.parents and path != POWAN_WORK_ROOT.resolve():
        raise HTTPException(status_code=400, detail="Invalid project path")
    return path


def powan_path(project: str, name: str = DEFAULT_FILE) -> Path:
    root = project_root(project)
    path = (root / safe_powan_name(name)).resolve()
    if root not in path.parents and path != root:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return path


def safe_attachment_stem(name: str) -> str:
    stem = Path(name or "clipboard").stem.strip() or "clipboard"
    invalid_chars = set('<>:"/\\|?*')
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in stem)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return (cleaned or "clipboard")[:80]


def split_image_data_url(data_url: str) -> tuple[str, bytes]:
    header, separator, encoded = data_url.partition(",")
    if not separator or not header.lower().startswith("data:image/") or ";base64" not in header.lower():
        raise HTTPException(status_code=400, detail="Invalid image data")
    mime = header[5:].split(";", 1)[0].lower()
    if mime not in IMAGE_MIME_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc
    if len(raw) > INLINE_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")
    return mime, raw


def save_inline_image_attachment(project: str, attachment: dict[str, Any], data_url: str) -> dict[str, Any]:
    mime, raw = split_image_data_url(data_url)
    root = project_root(project).resolve()
    attachment_root = (root / "data" / "attachments").resolve()
    if root not in attachment_root.parents and attachment_root != root:
        raise HTTPException(status_code=400, detail="Invalid attachment path")
    attachment_root.mkdir(parents=True, exist_ok=True)
    stem = safe_attachment_stem(str(attachment.get("name") or "clipboard"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid4().hex[:10]}_{stem}{IMAGE_MIME_EXTENSIONS[mime]}"
    path = (attachment_root / filename).resolve()
    if attachment_root not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid attachment path")
    path.write_bytes(raw)
    relative_path = path.relative_to(root).as_posix()
    next_attachment = dict(attachment)
    next_attachment.pop("imageDataUrl", None)
    next_attachment.update(
        {
            "kind": "image",
            "source": str(next_attachment.get("source") or "clipboard"),
            "name": str(next_attachment.get("name") or filename),
            "mime": mime,
            "size": len(raw),
            "path": str(path),
            "relativePath": relative_path,
            "pathAvailable": True,
        }
    )
    log_server_event(
        "info",
        "conversation-inline-image-saved",
        {
            "project": safe_project_name(project),
            "name": next_attachment["name"],
            "relativePath": relative_path,
            "size": len(raw),
        },
    )
    return next_attachment


def materialize_conversation_attachments(project: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for attachment in attachments[:20]:
        if not isinstance(attachment, dict):
            continue
        next_attachment = dict(attachment)
        data_url = str(next_attachment.get("imageDataUrl") or "")
        if data_url:
            next_attachment = save_inline_image_attachment(project, next_attachment, data_url)
        else:
            next_attachment.pop("imageDataUrl", None)
        next_attachment["pathAvailable"] = bool(next_attachment.get("path"))
        materialized.append(next_attachment)
    return materialized


def safe_sound_name(name: str) -> str:
    safe_name = Path(name).name
    if safe_name != name or not safe_name:
        raise HTTPException(status_code=400, detail="Invalid sound file name")
    if Path(safe_name).suffix.lower() not in SOUND_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported sound file")
    return safe_name


def resolve_sound_root(value: str | None) -> Path:
    raw = str(value or "").strip()
    path = DEFAULT_SOUND_ROOT if not raw else Path(raw).expanduser()
    if not path.is_absolute():
        path = APP_ROOT / path
    return path.resolve()


def ensure_sound_root(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Sound folder cannot be created: {exc}") from exc
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Sound root is not a folder")
    return path


def clamp_sound_volume(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_CONVERSATION_SOUND_VOLUME
    return min(1.0, max(0.0, number))


def clamp_auto_summary_turns(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = DEFAULT_AUTO_SUMMARY_TURNS
    return min(MAX_AUTO_SUMMARY_TURNS, max(MIN_AUTO_SUMMARY_TURNS, number))


def clamp_arrange_spacing(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_ARRANGE_SPACING
    return min(MAX_ARRANGE_SPACING, max(MIN_ARRANGE_SPACING, number))


def clamp_arrange_size(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_ARRANGE_SIZE
    return min(MAX_ARRANGE_SIZE, max(MIN_ARRANGE_SIZE, number))


def clamp_nested_layer_scale(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.5
    return min(1.0, max(0.3, number))


def normalize_codex_sandbox(value: Any) -> str:
    sandbox = str(value or "").strip()
    return sandbox if sandbox in CODEX_SANDBOXES else DEFAULT_CODEX_SANDBOX


def stable_for_signature(value: Any) -> Any:
    if isinstance(value, list):
        return [stable_for_signature(item) for item in value]
    if isinstance(value, dict):
        return {key: stable_for_signature(value[key]) for key in sorted(value)}
    return value


def document_signature(document: dict[str, Any]) -> str:
    stable_json = json.dumps(stable_for_signature(document), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def pick_sound_folder_with_explorer(initial_path: Path) -> Path | None:
    if os.name != "nt":
        raise HTTPException(status_code=400, detail="Folder picker is only supported on Windows")
    script = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class ModernFolderPicker
{{
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    private static extern void SHCreateItemFromParsingName(
        [MarshalAs(UnmanagedType.LPWStr)] string pszPath,
        IntPtr pbc,
        ref Guid riid,
        [MarshalAs(UnmanagedType.Interface)] out IShellItem ppv);

    [ComImport]
    [Guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")]
    private class FileOpenDialogRCW
    {{
    }}

    [ComImport]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    [Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE")]
    private interface IShellItem
    {{
        void BindToHandler(IntPtr pbc, ref Guid bhid, ref Guid riid, out IntPtr ppv);
        void GetParent(out IShellItem ppsi);
        void GetDisplayName(SIGDN sigdnName, [MarshalAs(UnmanagedType.LPWStr)] out string ppszName);
        void GetAttributes(uint sfgaoMask, out uint psfgaoAttribs);
        void Compare(IShellItem psi, uint hint, out int piOrder);
    }}

    private enum SIGDN : uint
    {{
        FILESYSPATH = 0x80058000
    }}

    [Flags]
    private enum FOS : uint
    {{
        PICKFOLDERS = 0x20,
        FORCEFILESYSTEM = 0x40,
        NOCHANGEDIR = 0x8,
        PATHMUSTEXIST = 0x800
    }}

    [ComImport]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    [Guid("D57C7288-D4AD-4768-BE02-9D969532D960")]
    private interface IFileOpenDialog
    {{
        [PreserveSig]
        int Show(IntPtr parent);
        void SetFileTypes(uint cFileTypes, IntPtr rgFilterSpec);
        void SetFileTypeIndex(uint iFileType);
        void GetFileTypeIndex(out uint piFileType);
        void Advise(IntPtr pfde, out uint pdwCookie);
        void Unadvise(uint dwCookie);
        void SetOptions(FOS fos);
        void GetOptions(out FOS pfos);
        void SetDefaultFolder(IShellItem psi);
        void SetFolder(IShellItem psi);
        void GetFolder(out IShellItem ppsi);
        void GetCurrentSelection(out IShellItem ppsi);
        void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string pszName);
        void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string pszName);
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string pszTitle);
        void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string pszText);
        void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string pszLabel);
        void GetResult(out IShellItem ppsi);
        void AddPlace(IShellItem psi, uint fdap);
        void SetDefaultExtension([MarshalAs(UnmanagedType.LPWStr)] string pszDefaultExtension);
        void Close(int hr);
        void SetClientGuid(ref Guid guid);
        void ClearClientData();
        void SetFilter(IntPtr pFilter);
        void GetResults(out IntPtr ppenum);
        void GetSelectedItems(out IntPtr ppsai);
    }}

    public static string Pick(string title, string initialPath)
    {{
        IFileOpenDialog dialog = (IFileOpenDialog)new FileOpenDialogRCW();
        FOS options;
        dialog.GetOptions(out options);
        dialog.SetOptions(options | FOS.PICKFOLDERS | FOS.FORCEFILESYSTEM | FOS.PATHMUSTEXIST | FOS.NOCHANGEDIR);
        dialog.SetTitle(title);
        dialog.SetOkButtonLabel("このフォルダを使う");
        if (!String.IsNullOrWhiteSpace(initialPath) && System.IO.Directory.Exists(initialPath))
        {{
            Guid shellItemGuid = new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE");
            IShellItem folder;
            SHCreateItemFromParsingName(initialPath, IntPtr.Zero, ref shellItemGuid, out folder);
            dialog.SetFolder(folder);
        }}
        int hr = dialog.Show(IntPtr.Zero);
        const int errorCancelled = unchecked((int)0x800704C7);
        if (hr == errorCancelled)
        {{
            return "";
        }}
        if (hr != 0)
        {{
            Marshal.ThrowExceptionForHR(hr);
        }}
        IShellItem result;
        dialog.GetResult(out result);
        string path;
        result.GetDisplayName(SIGDN.FILESYSPATH, out path);
        return path ?? "";
    }}
}}
"@
[ModernFolderPicker]::Pick('ABC Canvas サウンドフォルダ', {powershell_single_quoted(str(initial_path))})
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Folder picker timed out") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Folder picker failed: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Folder picker failed").strip()
        raise HTTPException(status_code=500, detail=detail)
    selected = result.stdout.strip()
    if not selected:
        return None
    return Path(selected).resolve()


def load_app_settings() -> dict[str, Any]:
    data: dict[str, Any] = {}
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log_server_event("warn", "settings-load-failed", {"message": str(exc)})
            data = {}
    try:
        sound_root = ensure_sound_root(resolve_sound_root(str(data.get("soundRoot") or "")))
    except HTTPException:
        sound_root = ensure_sound_root(DEFAULT_SOUND_ROOT.resolve())
    return {
        "soundRoot": str(sound_root),
        "conversationSound": str(data.get("conversationSound") or ""),
        "conversationSoundVolume": clamp_sound_volume(data.get("conversationSoundVolume", DEFAULT_CONVERSATION_SOUND_VOLUME)),
        "inputSound": str(data.get("inputSound") or ""),
        "inputSoundVolume": clamp_sound_volume(data.get("inputSoundVolume", DEFAULT_INPUT_SOUND_VOLUME)),
        "autoSummaryEnabled": bool(data.get("autoSummaryEnabled", DEFAULT_AUTO_SUMMARY_ENABLED)),
        "autoSummaryTurns": clamp_auto_summary_turns(data.get("autoSummaryTurns", DEFAULT_AUTO_SUMMARY_TURNS)),
        "codexSandbox": normalize_codex_sandbox(data.get("codexSandbox", DEFAULT_CODEX_SANDBOX)),
        "arrangeSpacing": clamp_arrange_spacing(data.get("arrangeSpacing", DEFAULT_ARRANGE_SPACING)),
        "arrangeSize": clamp_arrange_size(data.get("arrangeSize", DEFAULT_ARRANGE_SIZE)),
        "arrangeResizeParents": bool(data.get("arrangeResizeParents", True)),
        "arrangeRecursive": bool(data.get("arrangeRecursive", True)),
        "arrangeChildSpacing": clamp_arrange_spacing(data.get("arrangeChildSpacing", data.get("arrangeSpacing", DEFAULT_ARRANGE_SPACING))),
        "arrangeChildSize": clamp_arrange_size(data.get("arrangeChildSize", data.get("arrangeSize", DEFAULT_ARRANGE_SIZE))),
        "arrangeNestedChildSize": clamp_arrange_size(data.get("arrangeNestedChildSize", data.get("arrangeSize", DEFAULT_ARRANGE_SIZE))),
        "arrangeWorldParentSpacing": clamp_arrange_spacing(data.get("arrangeWorldParentSpacing", data.get("arrangeSpacing", DEFAULT_ARRANGE_SPACING))),
        "arrangeWorldParentSize": clamp_arrange_size(data.get("arrangeWorldParentSize", data.get("arrangeSize", DEFAULT_ARRANGE_SIZE))),
        "nestedLayerScale": clamp_nested_layer_scale(data.get("nestedLayerScale", 0.5)),
        "restartVisibleConsole": bool(data.get("restartVisibleConsole", False)),
        "consoleLogLevels": normalize_console_log_levels(data.get("consoleLogLevels")),
    }


def save_app_settings(settings: dict[str, Any]) -> None:
    SETTING_ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def current_sound_root() -> Path:
    return ensure_sound_root(Path(load_app_settings()["soundRoot"]))


def list_sound_files(sound_root: Path) -> list[dict[str, str]]:
    return [
        {"name": path.name, "url": f"/api/settings/sounds/{path.name}"}
        for path in sorted(sound_root.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.suffix.lower() in SOUND_EXTENSIONS
    ]


def setting_payload() -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(Path(settings["soundRoot"]))
    sounds = list_sound_files(sound_root)
    if settings["conversationSound"] and not any(sound["name"] == settings["conversationSound"] for sound in sounds):
        settings["conversationSound"] = ""
        save_app_settings(settings)
    if settings["inputSound"] and not any(sound["name"] == settings["inputSound"] for sound in sounds):
        settings["inputSound"] = ""
        save_app_settings(settings)
    return {
        "soundRoot": settings["soundRoot"],
        "defaultSoundRoot": str(DEFAULT_SOUND_ROOT.resolve()),
        "conversationSound": settings["conversationSound"],
        "conversationSoundVolume": settings["conversationSoundVolume"],
        "inputSound": settings["inputSound"],
        "inputSoundVolume": settings["inputSoundVolume"],
        "autoSummaryEnabled": settings["autoSummaryEnabled"],
        "autoSummaryTurns": settings["autoSummaryTurns"],
        "codexSandbox": settings["codexSandbox"],
        "arrangeSpacing": settings["arrangeSpacing"],
        "arrangeSize": settings["arrangeSize"],
        "arrangeResizeParents": settings["arrangeResizeParents"],
        "arrangeRecursive": settings["arrangeRecursive"],
        "arrangeChildSpacing": settings["arrangeChildSpacing"],
        "arrangeChildSize": settings["arrangeChildSize"],
        "arrangeNestedChildSize": settings["arrangeNestedChildSize"],
        "arrangeWorldParentSpacing": settings["arrangeWorldParentSpacing"],
        "arrangeWorldParentSize": settings["arrangeWorldParentSize"],
        "nestedLayerScale": settings["nestedLayerScale"],
        "restartVisibleConsole": settings["restartVisibleConsole"],
        "consoleLogLevels": settings["consoleLogLevels"],
        "sounds": sounds,
    }


def random_powan_style() -> dict[str, Any]:
    pair = random.choice(POWAN_COLOR_PALETTE)
    return {
        "shape": "cloud",
        "color": pair["color"],
        "accent": pair["accent"],
        "glow": True,
        "blur": True,
        "motion": "soft",
    }


def default_powan_style() -> dict[str, Any]:
    return {
        "shape": "cloud",
        "color": "#ffffff",
        "accent": "#8ddcff",
        "glow": True,
        "blur": True,
        "motion": "soft",
    }


def blank_document(random_color: bool = False) -> dict[str, Any]:
    return {
        "version": 1,
        "canvas": {
            "background": "#e8f8ff",
            "workspace": {
                "version": 1,
                "width": WORKSPACE_SIZE,
                "height": WORKSPACE_SIZE,
                "origin": {
                    "x": WORKSPACE_ORIGIN_X,
                    "y": WORKSPACE_ORIGIN_Y,
                },
            },
        },
        "nodes": [
            {
                "id": f"node-{uuid4().hex[:10]}",
                "title": "",
                "body": "",
                "code": "",
                "parent": None,
                "children": [],
                "style": random_powan_style() if random_color else default_powan_style(),
                "layout": {
                    "x": WORKSPACE_ORIGIN_X - DEFAULT_NODE_WIDTH // 2,
                    "y": WORKSPACE_ORIGIN_Y - DEFAULT_NODE_HEIGHT // 2,
                    "width": DEFAULT_NODE_WIDTH,
                    "height": DEFAULT_NODE_HEIGHT,
                },
            }
        ],
    }


def ensure_project(project: str) -> Path:
    return STORE.ensure_project(project)


STORE = PowanStore(POWAN_WORK_ROOT, DEFAULT_FILE, blank_document, log_server_event)
CODEX_BRIDGE = CodexPowanBridge(log_server_event)


app.include_router(create_ai_router(STORE, DEFAULT_FILE, log_server_event))


@app.get("/")
def index() -> FileResponse:
    return no_cache_file(STATIC_ROOT / "project.html")


@app.get("/canvas")
def canvas() -> FileResponse:
    return no_cache_file(STATIC_ROOT / "index.html")


@app.get("/settings")
def settings_page() -> FileResponse:
    return no_cache_file(STATIC_ROOT / "settings.html")


@app.get("/api/projects")
def list_projects() -> dict[str, list[dict[str, str]]]:
    projects = [
        {
            "name": path.name,
            "path": str(path),
        }
        for path in sorted(POWAN_WORK_ROOT.iterdir(), key=lambda item: item.name)
        if path.is_dir()
    ]
    return {"projects": projects}


@app.post("/api/projects")
def create_project(request: ProjectCreateRequest) -> dict[str, str]:
    name = STORE.safe_project_name(request.name)
    root = ensure_project(name)
    return {
        "name": name,
        "root": str(root),
        "file": DEFAULT_FILE,
    }


@app.post("/api/projects/open")
def open_project_root(request: ProjectCreateRequest) -> dict[str, str]:
    name = STORE.safe_project_name(request.name)
    root = ensure_project(name)
    subprocess.Popen(["explorer", str(root)])
    return {
        "status": "opened",
        "name": name,
        "root": str(root),
    }


@app.get("/api/files")
def list_files(project: str) -> dict[str, list[str]]:
    return {"files": STORE.list_documents(project)}


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    return setting_payload()


@app.post("/api/settings/sound-folder")
def save_sound_folder(request: SoundFolderRequest) -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(resolve_sound_root(request.soundRoot))
    sounds = list_sound_files(sound_root)
    settings["soundRoot"] = str(sound_root)
    if settings["conversationSound"] and not any(sound["name"] == settings["conversationSound"] for sound in sounds):
        settings["conversationSound"] = ""
    if settings["inputSound"] and not any(sound["name"] == settings["inputSound"] for sound in sounds):
        settings["inputSound"] = ""
    save_app_settings(settings)
    log_server_event("info", "sound-folder-updated", {"soundRoot": settings["soundRoot"]})
    return setting_payload()


@app.post("/api/settings/sound-folder/pick")
def pick_sound_folder() -> dict[str, Any]:
    settings = load_app_settings()
    selected = pick_sound_folder_with_explorer(Path(settings["soundRoot"]))
    if selected is None:
        log_server_event("info", "sound-folder-pick-cancelled", {"soundRoot": settings["soundRoot"]})
        payload = setting_payload()
        payload["cancelled"] = True
        return payload
    sound_root = ensure_sound_root(selected)
    sounds = list_sound_files(sound_root)
    settings["soundRoot"] = str(sound_root)
    if settings["conversationSound"] and not any(sound["name"] == settings["conversationSound"] for sound in sounds):
        settings["conversationSound"] = ""
    if settings["inputSound"] and not any(sound["name"] == settings["inputSound"] for sound in sounds):
        settings["inputSound"] = ""
    save_app_settings(settings)
    log_server_event("info", "sound-folder-picked", {"soundRoot": settings["soundRoot"]})
    payload = setting_payload()
    payload["cancelled"] = False
    return payload


@app.post("/api/settings/conversation-sound")
def save_conversation_sound(request: ConversationSoundRequest) -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(Path(settings["soundRoot"]))
    sound_name = request.conversationSound.strip()
    if sound_name:
        safe_name = safe_sound_name(sound_name)
        path = (sound_root / safe_name).resolve()
        if sound_root.resolve() not in path.parents or not path.exists() or not path.is_file():
            raise HTTPException(status_code=400, detail="Sound file not found")
        sound_name = safe_name
    settings["conversationSound"] = sound_name
    save_app_settings(settings)
    log_server_event("info", "conversation-sound-updated", {"conversationSound": sound_name})
    return setting_payload()


@app.post("/api/settings/conversation-sound-volume")
def save_conversation_sound_volume(request: ConversationSoundVolumeRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["conversationSoundVolume"] = clamp_sound_volume(request.conversationSoundVolume)
    save_app_settings(settings)
    log_server_event("info", "conversation-sound-volume-updated", {"volume": settings["conversationSoundVolume"]})
    return setting_payload()


@app.post("/api/settings/input-sound")
def save_input_sound(request: InputSoundRequest) -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(Path(settings["soundRoot"]))
    sound_name = request.inputSound.strip()
    if sound_name:
        safe_name = safe_sound_name(sound_name)
        path = (sound_root / safe_name).resolve()
        if sound_root.resolve() not in path.parents or not path.exists() or not path.is_file():
            raise HTTPException(status_code=400, detail="Sound file not found")
        sound_name = safe_name
    settings["inputSound"] = sound_name
    save_app_settings(settings)
    log_server_event("info", "input-sound-updated", {"inputSound": sound_name})
    return setting_payload()


@app.post("/api/settings/input-sound-volume")
def save_input_sound_volume(request: InputSoundVolumeRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["inputSoundVolume"] = clamp_sound_volume(request.inputSoundVolume)
    save_app_settings(settings)
    log_server_event("info", "input-sound-volume-updated", {"volume": settings["inputSoundVolume"]})
    return setting_payload()


@app.post("/api/settings/conversation-auto-summary")
def save_conversation_auto_summary(request: ConversationAutoSummaryRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["autoSummaryEnabled"] = bool(request.enabled)
    settings["autoSummaryTurns"] = clamp_auto_summary_turns(request.turns)
    save_app_settings(settings)
    log_server_event(
        "info",
        "conversation-auto-summary-updated",
        {
            "enabled": settings["autoSummaryEnabled"],
            "turns": settings["autoSummaryTurns"],
        },
    )
    return setting_payload()


@app.post("/api/settings/codex-sandbox")
def save_codex_sandbox(request: CodexSandboxRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["codexSandbox"] = normalize_codex_sandbox(request.codexSandbox)
    save_app_settings(settings)
    log_server_event("info", "codex-sandbox-updated", {"codexSandbox": settings["codexSandbox"]})
    return setting_payload()


@app.post("/api/settings/arrange")
def save_arrange_settings(request: ArrangeSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["arrangeSpacing"] = clamp_arrange_spacing(request.arrangeSpacing)
    settings["arrangeSize"] = clamp_arrange_size(request.arrangeSize)
    settings["arrangeResizeParents"] = bool(request.arrangeResizeParents)
    settings["arrangeRecursive"] = bool(request.arrangeRecursive)
    settings["arrangeChildSpacing"] = clamp_arrange_spacing(request.arrangeChildSpacing if request.arrangeChildSpacing is not None else request.arrangeSpacing)
    settings["arrangeChildSize"] = clamp_arrange_size(request.arrangeChildSize if request.arrangeChildSize is not None else request.arrangeSize)
    settings["arrangeNestedChildSize"] = clamp_arrange_size(request.arrangeNestedChildSize if request.arrangeNestedChildSize is not None else request.arrangeSize)
    settings["arrangeWorldParentSpacing"] = clamp_arrange_spacing(
        request.arrangeWorldParentSpacing if request.arrangeWorldParentSpacing is not None else request.arrangeSpacing
    )
    settings["arrangeWorldParentSize"] = clamp_arrange_size(request.arrangeWorldParentSize if request.arrangeWorldParentSize is not None else request.arrangeSize)
    settings["nestedLayerScale"] = clamp_nested_layer_scale(request.nestedLayerScale if request.nestedLayerScale is not None else 0.5)
    save_app_settings(settings)
    log_server_event(
        "info",
        "arrange-settings-updated",
        {
            "resizeParents": settings["arrangeResizeParents"],
            "recursive": settings["arrangeRecursive"],
            "childSpacing": settings["arrangeChildSpacing"],
            "childSize": settings["arrangeChildSize"],
            "nestedSize": settings["arrangeNestedChildSize"],
            "worldSpacing": settings["arrangeWorldParentSpacing"],
            "worldSize": settings["arrangeWorldParentSize"],
            "nestedLayerScale": settings["nestedLayerScale"],
        },
    )
    return setting_payload()


@app.post("/api/settings/console-log-levels")
def save_console_log_levels(request: ConsoleLogSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["consoleLogLevels"] = normalize_console_log_levels(request.consoleLogLevels)
    save_app_settings(settings)
    levels = ",".join(settings["consoleLogLevels"])
    log_server_event(
        "info",
        "console-log-levels-updated",
        {
            "message": f"console log levels updated: {levels}",
            "consoleLogLevels": settings["consoleLogLevels"],
            "console": True,
        },
    )
    return setting_payload()


@app.post("/api/settings/restart-visible-console")
def save_restart_visible_console(request: RestartVisibleConsoleSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["restartVisibleConsole"] = bool(request.restartVisibleConsole)
    save_app_settings(settings)
    log_server_event("info", "restart-visible-console-updated", {"restartVisibleConsole": settings["restartVisibleConsole"]})
    return setting_payload()


@app.get("/api/settings/sounds")
def list_sounds() -> dict[str, list[dict[str, str]]]:
    return {"sounds": list_sound_files(current_sound_root())}


@app.get("/api/settings/sounds/{name}")
def get_sound(name: str) -> FileResponse:
    safe_name = safe_sound_name(name)
    sound_root = current_sound_root()
    path = (sound_root / safe_name).resolve()
    if sound_root.resolve() not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Sound file not found")
    return FileResponse(path)


@app.get("/api/doc/{name}")
def load_doc(name: str, project: str) -> dict[str, Any]:
    data = STORE.load_document(project, name)
    return AbcDocument.model_validate(data).model_dump()


@app.post("/api/doc/{name}")
def save_doc(
    name: str,
    document: AbcDocument,
    project: str,
    x_abc_document_snapshot: str | None = Header(default=None),
) -> dict[str, str]:
    document_name = STORE.safe_powan_name(name)
    client_snapshot = unquote(x_abc_document_snapshot) if x_abc_document_snapshot is not None else None
    try:
        current_document = STORE.load_document(project, document_name)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        current_document = None
    if current_document is not None and not client_snapshot:
        log_server_event(
            "warn",
            "save-document-missing-snapshot-rejected",
            {
                "message": f"save rejected: missing snapshot {document_name}",
                "project": STORE.safe_project_name(project),
                "file": document_name,
                "clientNodes": len(document.nodes),
                "serverNodes": len(current_document.get("nodes") or []),
                "console": True,
            },
        )
        raise HTTPException(status_code=428, detail="Document snapshot is required")
    if current_document is not None:
        current_snapshot = document_signature(current_document)
        if current_snapshot != client_snapshot:
            log_server_event(
                "warn",
                "save-document-stale-rejected",
                {
                    "message": f"save rejected: stale snapshot {document_name}",
                    "project": STORE.safe_project_name(project),
                    "file": document_name,
                    "clientNodes": len(document.nodes),
                    "serverNodes": len(current_document.get("nodes") or []),
                    "console": True,
                },
            )
            raise HTTPException(status_code=409, detail="Document changed on server")
    payload = document.model_dump()
    STORE.save_document(project, document_name, payload, write_export=True)
    log_server_event(
        "info",
        "save-document-persist-complete",
        {
            "message": f"document persisted: {document_name}, {len(payload.get('nodes') or [])} nodes",
            "project": STORE.safe_project_name(project),
            "file": document_name,
            "nodeCount": len(payload.get("nodes") or []),
            "console": True,
        },
    )
    return {
        "status": "saved",
        "project": STORE.safe_project_name(project),
        "file": document_name,
        "snapshot": document_signature(payload),
    }


@app.post("/api/doc")
def create_doc(project: str, random_color: bool = False) -> dict[str, str]:
    ensure_project(project)
    name = f"canvas-{uuid4().hex[:8]}.powan"
    STORE.save_document(project, name, blank_document(random_color=random_color), write_export=True)
    return {"project": STORE.safe_project_name(project), "file": name}


def ensure_powan_exists(project: str, file: str, node_id: str) -> None:
    document = STORE.load_document(project, file)
    if not any(str(node.get("id")) == node_id for node in document.get("nodes") or []):
        raise HTTPException(status_code=404, detail="Powan not found")


def powan_label_from_document(document: dict[str, Any], node_id: str | None) -> str:
    if not node_id:
        return "ユーザー"
    for node in document.get("nodes") or []:
        if isinstance(node, dict) and str(node.get("id") or "") == str(node_id):
            return str(node.get("title") or node.get("body") or "名前のないポワン").strip() or "名前のないポワン"
    return "名前のないポワン"


def powan_work_message(status: str, sender_label: str, receiver_label: str, source: str) -> str:
    status_labels = {
        "received": "受信",
        "working": "作業中",
        "completed": "完了",
        "failed": "失敗",
        "cancelled": "キャンセル",
    }
    return f"{sender_label} -> {receiver_label} / {status_labels.get(status, status)}"


def remember_powan_work_event(details: dict[str, Any]) -> dict[str, Any]:
    global POWAN_WORK_EVENT_SEQUENCE
    with POWAN_WORK_EVENT_LOCK:
        POWAN_WORK_EVENT_SEQUENCE += 1
        event = {
            "sequence": POWAN_WORK_EVENT_SEQUENCE,
            "time": datetime.now().isoformat(timespec="milliseconds"),
            **details,
        }
        POWAN_WORK_EVENTS.append(event)
        del POWAN_WORK_EVENTS[:-POWAN_WORK_EVENT_LIMIT]
        return event


def log_powan_work_status(
    status: str,
    *,
    project: str,
    file: str,
    source: str,
    receiver_id: str,
    receiver_label: str,
    sender_id: str | None = None,
    sender_label: str = "ユーザー",
    conversation_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    details: dict[str, Any] = {
        "console": True,
        "message": powan_work_message(status, sender_label, receiver_label, source),
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "source": source,
        "status": status,
        "from": {
            "id": sender_id,
            "meaning": sender_label,
        },
        "to": {
            "id": receiver_id,
            "meaning": receiver_label,
        },
    }
    if conversation_id is not None:
        details["conversationId"] = conversation_id
    if extra:
        details.update(extra)
    remember_powan_work_event(details)
    log_server_event("info", f"powan-work-{status}", details)


def remember_powan_batch_work_event(
    *,
    status: str,
    message: str,
    project: str,
    file: str,
    source: str,
    sender_id: str,
    sender_label: str,
    receiver_label: str,
    count: int,
    instruction: str,
    extra: dict[str, Any] | None = None,
) -> None:
    details: dict[str, Any] = {
        "console": True,
        "message": message,
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "source": source,
        "status": status,
        "from": {
            "id": sender_id,
            "meaning": sender_label,
        },
        "to": {
            "id": None,
            "meaning": receiver_label,
        },
        "count": count,
        "instructionPreview": compact_console_text(instruction),
    }
    if extra:
        details.update(extra)
    remember_powan_work_event(details)


def run_powan_codex_message(
    node_id: str,
    *,
    project: str,
    file: str,
    text: str,
    include_meaning_tree: bool = False,
    include_direct_child_code: bool = False,
    attachments: list[dict[str, Any]] | None = None,
    source: str = "conversation",
    sender_node_id: str | None = None,
) -> dict[str, Any]:
    document = STORE.load_document(project, file)
    if not any(str(node.get("id")) == node_id for node in document.get("nodes") or []):
        raise HTTPException(status_code=404, detail="Powan not found")
    receiver_label = powan_label_from_document(document, node_id)
    sender_label = powan_label_from_document(document, sender_node_id) if sender_node_id else "ユーザー"
    materialized_attachments = materialize_conversation_attachments(project, attachments or [])
    conversation = STORE.active_conversation(project, file, node_id)
    log_powan_work_status(
        "received",
        project=project,
        file=file,
        source=source,
        sender_id=sender_node_id,
        sender_label=sender_label,
        receiver_id=node_id,
        receiver_label=receiver_label,
        conversation_id=conversation["id"],
        extra={
            "textPreview": compact_console_text(text),
            "messageLength": len(text.strip()),
            "includeMeaningTree": bool(include_meaning_tree),
            "includeDirectChildCode": bool(include_direct_child_code),
            "attachmentCount": len(materialized_attachments),
        },
    )
    user_message = STORE.append_conversation_message(
        project,
        file,
        node_id,
        "user",
        conversation_record_text(text, materialized_attachments),
    )
    messages = STORE.list_conversation_messages(project, file, node_id)["messages"]
    project_root_path = STORE.project_root(project)
    settings = load_app_settings()
    codex_sandbox = normalize_codex_sandbox(settings.get("codexSandbox"))
    log_server_event(
        "info",
        "codex-exec-start",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": conversation["id"],
            "source": source,
            "hasThread": bool(conversation.get("codexThreadId")),
            "messageLength": len(text.strip()),
            "includeMeaningTree": bool(include_meaning_tree),
            "includeDirectChildCode": bool(include_direct_child_code),
            "attachmentCount": len(materialized_attachments),
            "attachmentPathCount": sum(1 for attachment in materialized_attachments if isinstance(attachment, dict) and attachment.get("path")),
            "codexSandbox": codex_sandbox,
        },
    )
    log_powan_work_status(
        "working",
        project=project,
        file=file,
        source=source,
        sender_id=sender_node_id,
        sender_label=sender_label,
        receiver_id=node_id,
        receiver_label=receiver_label,
        conversation_id=conversation["id"],
        extra={
            "textPreview": compact_console_text(text),
            "hasThread": bool(conversation.get("codexThreadId")),
            "codexSandbox": codex_sandbox,
            "includeDirectChildCode": bool(include_direct_child_code),
        },
    )
    try:
        result = CODEX_BRIDGE.run(
            project_root=project_root_path,
            project=STORE.safe_project_name(project),
            document_name=STORE.safe_powan_name(file),
            document=document,
            node_id=node_id,
            user_text=text,
            conversation=conversation,
            messages=messages,
            include_meaning_tree=bool(include_meaning_tree),
            include_direct_child_code=bool(include_direct_child_code),
            attachments=materialized_attachments,
            codex_sandbox=codex_sandbox,
        )
    except Exception as exc:
        detail = f"Codex exec crashed before returning: {exc}"
        log_powan_work_status(
            "failed",
            project=project,
            file=file,
            source=source,
            sender_id=sender_node_id,
            sender_label=sender_label,
            receiver_id=node_id,
            receiver_label=receiver_label,
            conversation_id=conversation["id"],
            extra={
                "textPreview": compact_console_text(text),
                "error": repr(exc),
            },
        )
        log_server_event(
            "error",
            "codex-exec-crashed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "source": source,
                "error": repr(exc),
            },
        )
        STORE.record_agent_run(
            project,
            conversation["id"],
            node_id,
            "failed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "source": source,
                "userText": text,
            },
            error_text=detail,
        )
        raise HTTPException(status_code=502, detail=detail) from exc
    if result.thread_id and result.thread_id != conversation.get("codexThreadId"):
        STORE.set_conversation_codex_thread_id(project, conversation["id"], result.thread_id)
    run_payload = {
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "nodeId": node_id,
        "conversationId": conversation["id"],
        "threadId": result.thread_id,
        "resumed": result.resumed,
        "command": result.command,
        "durationMs": result.duration_ms,
        "source": source,
        "userText": text,
    }
    if result.cancelled:
        agent_run = STORE.record_agent_run(
            project,
            conversation["id"],
            node_id,
            "cancelled",
            run_payload,
            output_text=result.text,
            error_text=result.stderr[-4000:],
        )
        log_server_event(
            "info",
            "codex-exec-cancelled",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "threadId": result.thread_id,
                "source": source,
                "durationMs": result.duration_ms,
            },
        )
        log_powan_work_status(
            "cancelled",
            project=project,
            file=file,
            source=source,
            sender_id=sender_node_id,
            sender_label=sender_label,
            receiver_id=node_id,
            receiver_label=receiver_label,
            conversation_id=conversation["id"],
            extra={
                "textPreview": compact_console_text(text),
                "threadId": result.thread_id,
                "durationMs": result.duration_ms,
            },
        )
        return {
            "conversationId": conversation["id"],
            "codexThreadId": result.thread_id,
            "cancelled": True,
            "userMessage": user_message,
            "assistantMessage": None,
            "agentRun": agent_run,
        }
    if result.returncode != 0 or not result.text:
        STORE.record_agent_run(
            project,
            conversation["id"],
            node_id,
            "failed",
            run_payload,
            output_text=result.text,
            error_text=result.stderr[-4000:],
        )
        log_server_event(
            "error",
            "codex-exec-failed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "returncode": result.returncode,
                "source": source,
                "stderr": result.stderr[-1000:],
                "stdout": result.stdout[-1000:],
            },
        )
        log_powan_work_status(
            "failed",
            project=project,
            file=file,
            source=source,
            sender_id=sender_node_id,
            sender_label=sender_label,
            receiver_id=node_id,
            receiver_label=receiver_label,
            conversation_id=conversation["id"],
            extra={
                "textPreview": compact_console_text(text),
                "threadId": result.thread_id,
                "returncode": result.returncode,
                "durationMs": result.duration_ms,
            },
        )
        raise HTTPException(status_code=502, detail="Codex exec failed")
    assistant_message = STORE.append_conversation_message(project, file, node_id, "assistant", result.text)
    agent_run = STORE.record_agent_run(
        project,
        conversation["id"],
        node_id,
        "completed",
        run_payload,
        output_text=result.text,
        error_text=result.stderr[-4000:],
    )
    log_server_event(
        "info",
        "codex-exec-complete",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": conversation["id"],
            "threadId": result.thread_id,
            "resumed": result.resumed,
            "source": source,
            "durationMs": result.duration_ms,
            "outputLength": len(result.text),
        },
    )
    log_powan_work_status(
        "completed",
        project=project,
        file=file,
        source=source,
        sender_id=sender_node_id,
        sender_label=sender_label,
        receiver_id=node_id,
        receiver_label=receiver_label,
        conversation_id=conversation["id"],
        extra={
            "textPreview": compact_console_text(text),
            "threadId": result.thread_id,
            "durationMs": result.duration_ms,
            "outputLength": len(result.text),
        },
    )
    return {
        "conversationId": conversation["id"],
        "codexThreadId": result.thread_id,
        "userMessage": user_message,
        "assistantMessage": assistant_message,
        "agentRun": agent_run,
    }


def powan_label(node: dict[str, Any] | None) -> str:
    if not node:
        return "名前のないポワン"
    return str(node.get("title") or node.get("body") or "名前のないポワン").strip() or "名前のないポワン"


def document_nodes(document: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = document.get("nodes") or []
    return [node for node in nodes if isinstance(node, dict) and not node.get("archived")]


def document_node(document: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in document_nodes(document):
        if str(node.get("id") or "") == str(node_id):
            return node
    raise HTTPException(status_code=404, detail="Powan not found")


def document_direct_children(document: dict[str, Any], parent_id: str) -> list[dict[str, Any]]:
    return [node for node in document_nodes(document) if str(node.get("parent") or "") == str(parent_id)]


def match_child_command_target(children: list[dict[str, Any]], item: ChildCommandRequest) -> dict[str, Any]:
    child_id = str(item.childId or "").strip()
    title = item.title.strip()
    body = item.body.strip()
    if child_id:
        matches = [child for child in children if str(child.get("id") or "") == child_id]
    else:
        if not title and not body:
            raise HTTPException(status_code=400, detail="child title or body is required")
        matches = children
        if title:
            matches = [child for child in matches if str(child.get("title") or "").strip() == title]
        if body:
            matches = [child for child in matches if str(child.get("body") or "").strip() == body]
    if not matches:
        raise HTTPException(status_code=404, detail="Child powan not found")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="Multiple child powans matched")
    return matches[0]


def render_child_command(parent: dict[str, Any], child: dict[str, Any], instruction: str) -> str:
    return f"""親ポワン「{powan_label(parent)}」から、あなたへの命令です。
あなたは親ポワンの直接の子ポワン「{powan_label(child)}」として、この命令を実行してください。
必要な状態変更は `.agents/skills/abc-powan/TOOL.md` の操作を使ってください。

{instruction.strip()}
"""


def child_command_jobs(document: dict[str, Any], parent_id: str, request: CommandChildrenRequest) -> list[dict[str, str]]:
    parent = document_node(document, parent_id)
    children = document_direct_children(document, parent_id)
    if not children:
        raise HTTPException(status_code=400, detail="Child powans are required")
    common_instruction = request.instruction.strip()
    jobs_by_id: dict[str, dict[str, str]] = {}
    if common_instruction:
        for child in children:
            child_id = str(child.get("id") or "")
            if child_id:
                jobs_by_id[child_id] = {
                    "nodeId": child_id,
                    "meaning": powan_label(child),
                    "instruction": common_instruction,
                }
    for item in request.instructions:
        child = match_child_command_target(children, item)
        child_id = str(child.get("id") or "")
        if not child_id:
            continue
        individual_instruction = item.instruction.strip()
        if not individual_instruction and not common_instruction:
            raise HTTPException(status_code=400, detail="instruction is required")
        if child_id in jobs_by_id and not common_instruction:
            raise HTTPException(status_code=409, detail="Duplicate child command target")
        instruction = common_instruction
        if individual_instruction:
            instruction = f"{common_instruction}\n\n個別命令:\n{individual_instruction}".strip()
        jobs_by_id[child_id] = {
            "nodeId": child_id,
            "meaning": powan_label(child),
            "instruction": instruction,
        }
    if not jobs_by_id:
        raise HTTPException(status_code=400, detail="instruction or instructions is required")
    jobs: list[dict[str, str]] = []
    for child in children:
        child_id = str(child.get("id") or "")
        job = jobs_by_id.get(child_id)
        if job:
            jobs.append(
                {
                    **job,
                    "text": render_child_command(parent, child, job["instruction"]),
                }
            )
    return jobs


@app.get("/api/conversations/{node_id}")
def list_conversation_messages(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return STORE.list_conversation_messages(project, file, node_id)


@app.get("/api/conversations/{node_id}/sessions")
def list_conversation_sessions(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return STORE.list_conversation_sessions(project, file, node_id)


@app.get("/api/conversations/{node_id}/sessions/{conversation_id}")
def get_conversation_session(
    node_id: str,
    conversation_id: int,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return STORE.conversation_messages_by_id(project, file, node_id, conversation_id)


@app.post("/api/conversations/{node_id}/messages")
def append_conversation_message(
    node_id: str,
    request: ConversationMessageRequest,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return STORE.append_conversation_message(project, file, node_id, request.role, request.text)


@app.post("/api/conversations/{node_id}/sessions")
def start_new_conversation_session(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    conversation = STORE.start_new_conversation(project, file, node_id)
    payload = STORE.list_conversation_messages(project, file, node_id)
    log_server_event(
        "info",
        "conversation-session-started",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": conversation["id"],
        },
    )
    return {
        "conversationId": conversation["id"],
        "conversation": conversation,
        "messages": payload["messages"],
    }


@app.post("/api/conversations/{node_id}/summarize")
def summarize_conversation(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    messages = STORE.list_conversation_messages(project, file, node_id)["messages"]
    if not messages:
        conversation = STORE.start_new_conversation(project, file, node_id)
        return {
            "conversationId": conversation["id"],
            "conversation": conversation,
            "summary": "",
            "messages": [],
        }
    old_conversation = STORE.active_conversation(project, file, node_id)
    project_root_path = STORE.project_root(project)
    log_server_event(
        "info",
        "conversation-summary-start",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": old_conversation["id"],
            "messageCount": len(messages),
        },
    )
    try:
        result = CODEX_BRIDGE.summarize_conversation(
            project_root=project_root_path,
            project=STORE.safe_project_name(project),
            document_name=STORE.safe_powan_name(file),
            node_id=node_id,
            messages=messages,
        )
    except Exception as exc:
        detail = f"Codex exec crashed before summarizing: {exc}"
        log_server_event(
            "error",
            "conversation-summary-crashed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": old_conversation["id"],
                "error": repr(exc),
            },
        )
        raise HTTPException(status_code=502, detail=detail) from exc
    if result.returncode != 0 or not result.text:
        STORE.record_agent_run(
            project,
            old_conversation["id"],
            node_id,
            "failed",
            {
                "type": "conversation-summary",
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": old_conversation["id"],
                "durationMs": result.duration_ms,
                "inputChars": result.input_chars,
                "turnCount": result.turn_count,
                "retryCount": result.retry_count,
                "trimmedChars": result.trimmed_chars,
            },
            output_text=result.text,
            error_text=result.stderr[-4000:],
        )
        log_server_event(
            "error",
            "conversation-summary-failed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": old_conversation["id"],
                "returncode": result.returncode,
                "stderr": result.stderr[-1000:],
            },
        )
        raise HTTPException(status_code=502, detail="Codex exec summary failed")
    STORE.record_agent_run(
        project,
        old_conversation["id"],
        node_id,
        "completed",
        {
            "type": "conversation-summary",
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": old_conversation["id"],
            "durationMs": result.duration_ms,
            "inputChars": result.input_chars,
            "turnCount": result.turn_count,
            "retryCount": result.retry_count,
            "trimmedChars": result.trimmed_chars,
        },
        output_text=result.text,
        error_text=result.stderr[-4000:],
    )
    conversation = STORE.start_new_conversation(project, file, node_id, title="要約から再開", summary_text=result.text)
    payload = STORE.list_conversation_messages(project, file, node_id)
    log_server_event(
        "info",
        "conversation-summary-complete",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "oldConversationId": old_conversation["id"],
            "conversationId": conversation["id"],
            "summaryLength": len(result.text),
            "inputChars": result.input_chars,
            "turnCount": result.turn_count,
            "retryCount": result.retry_count,
            "trimmedChars": result.trimmed_chars,
        },
    )
    return {
        "conversationId": conversation["id"],
        "conversation": conversation,
        "summary": result.text,
        "inputChars": result.input_chars,
        "turnCount": result.turn_count,
        "retryCount": result.retry_count,
        "trimmedChars": result.trimmed_chars,
        "messages": payload["messages"],
    }


@app.post("/api/conversations/{node_id}/codex")
def talk_to_powan_with_codex(
    node_id: str,
    request: PowanCodexRequest,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    return run_powan_codex_message(
        node_id,
        project=project,
        file=file,
        text=request.text,
        include_meaning_tree=bool(request.includeMeaningTree),
        include_direct_child_code=bool(request.includeDirectChildCode),
        attachments=request.attachments,
        source="conversation",
    )


@app.get("/api/powan-work-events")
def list_powan_work_events(
    project: str,
    file: str = DEFAULT_FILE,
    after: int = 0,
    conversationId: int | None = None,
) -> dict[str, Any]:
    safe_project = STORE.safe_project_name(project)
    safe_file = STORE.safe_powan_name(file)
    with POWAN_WORK_EVENT_LOCK:
        events = [
            event
            for event in POWAN_WORK_EVENTS
            if int(event.get("sequence") or 0) > after
            and event.get("project") == safe_project
            and event.get("file") == safe_file
            and (conversationId is None or event.get("conversationId") == conversationId)
        ]
        latest_sequence = POWAN_WORK_EVENT_SEQUENCE
    return {
        "events": events,
        "latestSequence": latest_sequence,
    }


@app.post("/api/ai/powans/{node_id}/actions/command-children")
def command_child_powans(node_id: str, request: CommandChildrenRequest) -> dict[str, Any]:
    request_payload = base_model_payload(request)
    parent_label = "名前のないポワン"
    job_count = 0
    try:
        document = STORE.load_document(request.project, request.file)
        parent = document_node(document, node_id)
        parent_label = powan_label(parent)
        jobs = child_command_jobs(document, node_id, request)
        job_count = len(jobs)
        max_parallel = max(1, min(int(request.maxParallel or 1), 8))
        stagger_ms = max(0, min(int(request.staggerMs or 0), 60000))
        run_parallel = bool(request.parallel) and request.continueOnError and len(jobs) > 1 and max_parallel > 1
        results: list[dict[str, Any]] = []
        start_message = f"{parent_label} -> 子ポワン {len(jobs)}件 / 一括命令受信"
        log_server_event(
            "info",
            "command-child-powans-start",
            {
                "console": True,
                "message": start_message,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "count": len(jobs),
                "instructionPreview": compact_console_text(request.instruction),
                "includeMeaningTree": bool(request.includeMeaningTree),
                "parallel": run_parallel,
                "maxParallel": max_parallel,
                "staggerMs": stagger_ms,
                "request": request_payload,
            },
        )
        remember_powan_batch_work_event(
            status="received",
            message=start_message,
            project=request.project,
            file=request.file,
            source="command-children",
            sender_id=node_id,
            sender_label=parent_label,
            receiver_label=f"子ポワン {len(jobs)}件",
            count=len(jobs),
            instruction=request.instruction,
            extra={
                "includeMeaningTree": bool(request.includeMeaningTree),
                "parallel": run_parallel,
                "maxParallel": max_parallel,
                "staggerMs": stagger_ms,
            },
        )

        def run_job(index: int, job: dict[str, str]) -> dict[str, Any]:
            delay_ms = stagger_ms * index if run_parallel else 0
            if delay_ms:
                time.sleep(delay_ms / 1000)
            log_server_event(
                "trace",
                "command-child-powan-job-start",
                {
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "parentId": node_id,
                    "nodeId": job["nodeId"],
                    "index": index,
                    "delayMs": delay_ms,
                    "instruction": job["instruction"],
                },
            )
            try:
                result = run_powan_codex_message(
                    job["nodeId"],
                    project=request.project,
                    file=request.file,
                    text=job["text"],
                    include_meaning_tree=bool(request.includeMeaningTree),
                    attachments=[],
                    source="command-children",
                    sender_node_id=node_id,
                )
                item = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": "completed",
                    "conversationId": result.get("conversationId"),
                    "assistantMessage": result.get("assistantMessage"),
                    "agentRun": result.get("agentRun"),
                }
                log_server_event(
                    "trace",
                    "command-child-powan-job-complete",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "nodeId": job["nodeId"],
                        "index": index,
                        "status": "completed",
                    },
                )
                return item
            except HTTPException as exc:
                failure = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": "failed",
                    "error": exc.detail,
                    "httpStatus": exc.status_code,
                }
                log_server_event(
                    "error",
                    "command-child-powan-failed",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "nodeId": job["nodeId"],
                        "instruction": job["instruction"],
                        "renderedText": job["text"],
                        "error": exc.detail,
                    },
                )
                return failure
            except Exception as exc:
                failure = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": "failed",
                    "error": repr(exc),
                    "httpStatus": 500,
                }
                log_server_event(
                    "error",
                    "command-child-powan-failed",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "nodeId": job["nodeId"],
                        "instruction": job["instruction"],
                        "renderedText": job["text"],
                        "error": repr(exc),
                    },
                )
                return failure

        if run_parallel:
            ordered_results: list[dict[str, Any] | None] = [None] * len(jobs)
            with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                futures = {
                    executor.submit(run_job, index, job): index
                    for index, job in enumerate(jobs)
                }
                for future in as_completed(futures):
                    index = futures[future]
                    ordered_results[index] = future.result()
            results = [result for result in ordered_results if result is not None]
        else:
            for index, job in enumerate(jobs):
                result = run_job(index, job)
                results.append(result)
                if result.get("status") != "completed" and not request.continueOnError:
                    raise HTTPException(status_code=int(result.get("httpStatus") or 500), detail=result.get("error"))

        for result in results:
            result.pop("httpStatus", None)

        response = {
            "project": STORE.safe_project_name(request.project),
            "file": STORE.safe_powan_name(request.file),
            "parent": {"id": node_id, "meaning": powan_label(parent)},
            "parallel": run_parallel,
            "maxParallel": max_parallel,
            "staggerMs": stagger_ms,
            "results": results,
        }
        complete_message = f"{parent_label} -> 子ポワン {len(results)}件 / 一括命令完了"
        log_server_event(
            "info",
            "command-child-powans-complete",
            {
                "console": True,
                "message": complete_message,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "count": len(results),
                "failed": sum(1 for result in results if result.get("status") != "completed"),
                "instructionPreview": compact_console_text(request.instruction),
                "request": request_payload,
                "response": response,
            },
        )
        remember_powan_batch_work_event(
            status="completed",
            message=complete_message,
            project=request.project,
            file=request.file,
            source="command-children",
            sender_id=node_id,
            sender_label=parent_label,
            receiver_label=f"子ポワン {len(results)}件",
            count=len(results),
            instruction=request.instruction,
            extra={
                "failed": sum(1 for result in results if result.get("status") != "completed"),
                "parallel": run_parallel,
                "maxParallel": max_parallel,
                "staggerMs": stagger_ms,
            },
        )
        record_api_action_safely(
            project=request.project,
            file=request.file,
            node_id=node_id,
            action="command-children",
            status="completed",
            request_payload=request_payload,
            response_payload=response,
        )
        return response
    except HTTPException as exc:
        failed_message = f"{parent_label} -> 子ポワン {job_count or ''}件 / 一括命令失敗" if job_count else f"{parent_label} -> 子ポワン / 一括命令失敗"
        log_server_event(
            "error",
            "command-child-powans-failed",
            {
                "console": True,
                "message": failed_message,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "error": str(exc.detail),
            },
        )
        remember_powan_batch_work_event(
            status="failed",
            message=failed_message,
            project=request.project,
            file=request.file,
            source="command-children",
            sender_id=node_id,
            sender_label=parent_label,
            receiver_label=f"子ポワン {job_count}件" if job_count else "子ポワン",
            count=job_count,
            instruction=request.instruction,
            extra={"error": str(exc.detail)},
        )
        record_api_action_safely(
            project=request.project,
            file=request.file,
            node_id=node_id,
            action="command-children",
            status="failed",
            request_payload=request_payload,
            response_payload={},
            error_text=str(exc.detail),
        )
        raise
    except Exception as exc:
        failed_message = f"{parent_label} -> 子ポワン {job_count or ''}件 / 一括命令失敗" if job_count else f"{parent_label} -> 子ポワン / 一括命令失敗"
        log_server_event(
            "error",
            "command-child-powans-failed",
            {
                "console": True,
                "message": failed_message,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "error": repr(exc),
            },
        )
        remember_powan_batch_work_event(
            status="failed",
            message=failed_message,
            project=request.project,
            file=request.file,
            source="command-children",
            sender_id=node_id,
            sender_label=parent_label,
            receiver_label=f"子ポワン {job_count}件" if job_count else "子ポワン",
            count=job_count,
            instruction=request.instruction,
            extra={"error": repr(exc)},
        )
        record_api_action_safely(
            project=request.project,
            file=request.file,
            node_id=node_id,
            action="command-children",
            status="failed",
            request_payload=request_payload,
            response_payload={},
            error_text=repr(exc),
        )
        raise


@app.post("/api/conversations/{node_id}/codex/cancel")
def cancel_powan_codex(
    node_id: str,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    result = CODEX_BRIDGE.cancel(
        project=STORE.safe_project_name(project),
        document_name=STORE.safe_powan_name(file),
        node_id=node_id,
    )
    log_server_event(
        "info",
        "codex-exec-cancel-api",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            **result,
        },
    )
    return result


@app.post("/api/logs/client")
def write_client_logs(batch: ClientLogBatch) -> dict[str, int]:
    if not batch.entries:
        return {"written": 0}
    written = write_log_entries(batch.entries[:500])
    return {"written": written}


@app.post("/api/shutdown")
def shutdown_app(request: ShutdownRequest) -> dict[str, Any]:
    pids = shutdown_target_pids()
    log_server_event("info", "shutdown-requested", {"reason": request.reason, "targetPids": pids})
    threading.Thread(target=shutdown_later, args=(pids,), daemon=True).start()
    return {"status": "shutting down", "targetPids": pids}


@app.post("/api/restart")
def restart_app(request: RestartRequest) -> dict[str, Any]:
    pids = shutdown_target_pids()
    settings = load_app_settings()
    visible_console = bool(settings["restartVisibleConsole"] if request.visibleConsole is None else request.visibleConsole)
    log_server_event(
        "info",
        "restart-requested",
        {
            "reason": request.reason,
            "targetPids": pids,
            "visibleConsole": visible_console,
            "visibleConsoleSource": "settings" if request.visibleConsole is None else "request",
        },
    )
    threading.Thread(target=restart_later, args=(pids, visible_console), daemon=True).start()
    return {"status": "restarting", "targetPids": pids, "visibleConsole": visible_console}
