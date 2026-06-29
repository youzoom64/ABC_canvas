from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import queue
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import unquote
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from abc_discord_bridge import AbcDiscordBridge, normalize_discord_channel_id
from ai_api import create_ai_router
from codex_bridge import CodexPowanBridge
from powan_store import PowanStore
from project_scaffold import ensure_project_scaffold


APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
POWAN_WORK_ROOT = APP_ROOT / "powan_work"
CODEX_WORKSPACE_ROOT = APP_ROOT / ".codex_powan_workspaces"
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
DEFAULT_CODEX_MODEL = "gpt-5.5"
DEFAULT_CODEX_REASONING_EFFORT = "low"
CODEX_REASONING_EFFORTS = {"", "none", "minimal", "low", "medium", "high", "xhigh"}
CODEX_REASONING_EFFORT_ALIASES = {
    "very_high": "xhigh",
    "very-high": "xhigh",
}
DEFAULT_DISCORD_TOKEN_ENV = "DISCORD_BOT_TOKEN"
DEFAULT_DISCORD_MESSAGE_LIMIT = 1900
DEFAULT_ARRANGE_SPACING = 1.0
DEFAULT_ARRANGE_SIZE = 1.0
MIN_ARRANGE_SPACING = 0.3
MAX_ARRANGE_SPACING = 3.0
MIN_ARRANGE_SIZE = 0.3
MAX_ARRANGE_SIZE = 2.5
TITLE_FONT_FAMILIES = {
    "",
    "Dela Gothic One",
    "Hachi Maru Pop",
    "Klee One",
    "RocknRoll One",
    "New Tegomin",
    "Train One",
    "DotGothic16",
    "Reggae One",
    "Yuji Syuku",
    "Yuji Boku",
    "Mochiy Pop One",
    "Kaisei HarunoUmi",
    "Shippori Antique",
    "Stick",
    "Rampart One",
    "Zen Antique",
    "Mochiy Pop P One",
    "Zen Kurenaido",
    "Yusei Magic",
}
DEFAULT_TITLE_FONT_FAMILY = ""
DEFAULT_TITLE_FONT_SCALE = 1.0
MIN_TITLE_FONT_SCALE = 0.5
MAX_TITLE_FONT_SCALE = 2.0
DEFAULT_TITLE_OUTLINE_COLOR = "#ffffff"
DEFAULT_TITLE_OUTLINE_WIDTH = 1.5
MIN_TITLE_OUTLINE_WIDTH = 0.0
MAX_TITLE_OUTLINE_WIDTH = 6.0
DEFAULT_TITLE_SHADOW_COLOR = "#ffffff"
DEFAULT_TITLE_SHADOW_BLUR = 4.0
MIN_TITLE_SHADOW_BLUR = 0.0
MAX_TITLE_SHADOW_BLUR = 18.0
MIN_TITLE_SHADOW_OFFSET = -12.0
MAX_TITLE_SHADOW_OFFSET = 12.0
WORKSPACE_SIZE = 10000
WORKSPACE_ORIGIN_X = 5000
WORKSPACE_ORIGIN_Y = 5000
DEFAULT_NODE_WIDTH = 280
DEFAULT_NODE_HEIGHT = 160
CONSOLE_TEXT_PREVIEW_CHARS = 30
LOG_LEVEL_NAMES = ("trace", "debug", "info", "warn", "error", "fatal")
ORIGIN_CHAIN_SCHEMA = "powan_origin_chain.v1"
ORIGIN_JUDGEMENT_SCHEMA = "powan_origin_judgement.v1"
ORIGIN_JUDGEMENT_MAX_ATTEMPTS = 3
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
CODEX_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
SETTING_ROOT.mkdir(parents=True, exist_ok=True)
DEFAULT_SOUND_ROOT.mkdir(parents=True, exist_ok=True)
LOG_ROOT.mkdir(parents=True, exist_ok=True)

POWAN_WORK_EVENTS: list[dict[str, Any]] = []
POWAN_WORK_EVENT_SEQUENCE = 0
POWAN_WORK_EVENT_LOCK = threading.Lock()
COMMAND_CHILDREN_ACTIVE_LOCK = threading.Lock()
COMMAND_CHILDREN_ACTIVE_KEYS: set[str] = set()
PENDING_CODEX_DRAIN_LOCK = threading.Lock()
PENDING_CODEX_DRAIN_KEYS: set[str] = set()
CONVERSATION_EVENT_SUBSCRIBERS_LOCK = threading.Lock()
CONVERSATION_EVENT_SUBSCRIBERS: set[queue.Queue[dict[str, Any]]] = set()


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


def conversation_sse_frame(payload: dict[str, Any]) -> str:
    return f"event: conversation-message\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def publish_conversation_message(payload: dict[str, Any]) -> None:
    with CONVERSATION_EVENT_SUBSCRIBERS_LOCK:
        subscribers = list(CONVERSATION_EVENT_SUBSCRIBERS)
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(payload)
        except queue.Full:
            try:
                subscriber.get_nowait()
            except queue.Empty:
                pass
            try:
                subscriber.put_nowait(payload)
            except queue.Full:
                pass


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


class CodexModelSettingsRequest(BaseModel):
    codexModel: str = ""
    codexReasoningEffort: str = ""


class DiscordSettingsRequest(BaseModel):
    enabled: bool = False
    tokenEnv: str = DEFAULT_DISCORD_TOKEN_ENV
    channelId: str = ""
    project: str = ""
    file: str = DEFAULT_FILE
    targetNodeId: str = ""
    messageLimit: int = DEFAULT_DISCORD_MESSAGE_LIMIT


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


class TitleStyleSettingsRequest(BaseModel):
    titleFontFamily: str = DEFAULT_TITLE_FONT_FAMILY
    titleFontScale: float = DEFAULT_TITLE_FONT_SCALE
    titleOutlineEnabled: bool = False
    titleOutlineColor: str = DEFAULT_TITLE_OUTLINE_COLOR
    titleOutlineWidth: float = DEFAULT_TITLE_OUTLINE_WIDTH
    titleShadowEnabled: bool = True
    titleShadowColor: str = DEFAULT_TITLE_SHADOW_COLOR
    titleShadowBlur: float = DEFAULT_TITLE_SHADOW_BLUR
    titleShadowX: float = 0.0
    titleShadowY: float = 1.0


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
    skip: bool = False
    skipReason: str = ""
    status: str = ""


class CommandChildrenRequest(BaseModel):
    project: str
    file: str = DEFAULT_FILE
    instruction: str = ""
    instructions: list[ChildCommandRequest] = Field(default_factory=list)
    bulkHistoryId: str = ""
    includeMeaningTree: bool = False
    continueAfterChildReplies: bool = False
    originChain: list[dict[str, Any]] = Field(default_factory=list)


class BulkCommandHistoryMessage(BaseModel):
    role: str = "system"
    text: str = ""
    createdAt: str = ""


class BulkCommandHistoryRequest(BaseModel):
    project: str
    file: str = DEFAULT_FILE
    id: str
    targetIds: list[str] = Field(default_factory=list)
    targetNames: list[str] = Field(default_factory=list)
    messages: list[BulkCommandHistoryMessage] = Field(default_factory=list)
    createdAt: str = ""
    updatedAt: str = ""


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


def normalize_title_font_family(value: Any) -> str:
    clean = str(value or "").strip()
    return clean if clean in TITLE_FONT_FAMILIES else DEFAULT_TITLE_FONT_FAMILY


def normalize_hex_color(value: Any, fallback: str = "#ffffff") -> str:
    clean = str(value or "").strip().lower()
    if len(clean) == 7 and clean.startswith("#") and all(char in "0123456789abcdef" for char in clean[1:]):
        return clean
    return fallback


def clamp_title_font_scale(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_TITLE_FONT_SCALE
    return min(MAX_TITLE_FONT_SCALE, max(MIN_TITLE_FONT_SCALE, number))


def clamp_title_outline_width(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_TITLE_OUTLINE_WIDTH
    return min(MAX_TITLE_OUTLINE_WIDTH, max(MIN_TITLE_OUTLINE_WIDTH, number))


def clamp_title_shadow_blur(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_TITLE_SHADOW_BLUR
    return min(MAX_TITLE_SHADOW_BLUR, max(MIN_TITLE_SHADOW_BLUR, number))


def clamp_title_shadow_offset(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return min(MAX_TITLE_SHADOW_OFFSET, max(MIN_TITLE_SHADOW_OFFSET, number))


def normalize_codex_sandbox(value: Any) -> str:
    sandbox = str(value or "").strip()
    return sandbox if sandbox in CODEX_SANDBOXES else DEFAULT_CODEX_SANDBOX


def normalize_codex_model(value: Any) -> str:
    model = str(value or "").strip()
    return model[:120]


def normalize_codex_reasoning_effort(value: Any) -> str:
    effort = str(value or "").strip().lower()
    effort = CODEX_REASONING_EFFORT_ALIASES.get(effort, effort)
    return effort if effort in CODEX_REASONING_EFFORTS else DEFAULT_CODEX_REASONING_EFFORT


def normalize_discord_message_limit(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = DEFAULT_DISCORD_MESSAGE_LIMIT
    return min(2000, max(300, number))


def normalize_discord_settings(value: Any) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    project = str(data.get("project") or "").strip()
    file = str(data.get("file") or DEFAULT_FILE).strip() or DEFAULT_FILE
    if not file.endswith(".powan"):
        file = f"{file}.powan"
    return {
        "enabled": bool(data.get("enabled", False)),
        "tokenEnv": DEFAULT_DISCORD_TOKEN_ENV,
        "channelId": normalize_discord_channel_id(data.get("channelId") or ""),
        "project": project,
        "file": Path(file).name,
        "targetNodeId": str(data.get("targetNodeId") or "").strip(),
        "messageLimit": normalize_discord_message_limit(data.get("messageLimit")),
    }


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
        "codexModel": normalize_codex_model(data.get("codexModel", DEFAULT_CODEX_MODEL)),
        "codexReasoningEffort": normalize_codex_reasoning_effort(data.get("codexReasoningEffort", DEFAULT_CODEX_REASONING_EFFORT)),
        "discord": normalize_discord_settings(data.get("discord")),
        "titleFontFamily": normalize_title_font_family(data.get("titleFontFamily", DEFAULT_TITLE_FONT_FAMILY)),
        "titleFontScale": clamp_title_font_scale(data.get("titleFontScale", DEFAULT_TITLE_FONT_SCALE)),
        "titleOutlineEnabled": bool(data.get("titleOutlineEnabled", False)),
        "titleOutlineColor": normalize_hex_color(data.get("titleOutlineColor", "#ffffff"), "#ffffff"),
        "titleOutlineWidth": clamp_title_outline_width(data.get("titleOutlineWidth", DEFAULT_TITLE_OUTLINE_WIDTH)),
        "titleShadowEnabled": bool(data.get("titleShadowEnabled", True)),
        "titleShadowColor": normalize_hex_color(data.get("titleShadowColor", "#ffffff"), "#ffffff"),
        "titleShadowBlur": clamp_title_shadow_blur(data.get("titleShadowBlur", DEFAULT_TITLE_SHADOW_BLUR)),
        "titleShadowX": clamp_title_shadow_offset(data.get("titleShadowX", 0.0), 0.0),
        "titleShadowY": clamp_title_shadow_offset(data.get("titleShadowY", 1.0), 1.0),
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
        "codexModel": settings["codexModel"],
        "codexReasoningEffort": settings["codexReasoningEffort"],
        "discord": settings["discord"],
        "discordStatus": ABC_DISCORD_BRIDGE.status() if ABC_DISCORD_BRIDGE is not None else {},
        "titleFontFamily": settings["titleFontFamily"],
        "titleFontScale": settings["titleFontScale"],
        "titleOutlineEnabled": settings["titleOutlineEnabled"],
        "titleOutlineColor": settings["titleOutlineColor"],
        "titleOutlineWidth": settings["titleOutlineWidth"],
        "titleShadowEnabled": settings["titleShadowEnabled"],
        "titleShadowColor": settings["titleShadowColor"],
        "titleShadowBlur": settings["titleShadowBlur"],
        "titleShadowX": settings["titleShadowX"],
        "titleShadowY": settings["titleShadowY"],
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
STORE.on_conversation_message = publish_conversation_message
STORE.recover_interrupted_work(reason="server-startup")
CODEX_BRIDGE = CodexPowanBridge(log_server_event)
ABC_DISCORD_BRIDGE: AbcDiscordBridge | None = None


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


@app.post("/api/settings/codex-model")
def save_codex_model_settings(request: CodexModelSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["codexModel"] = normalize_codex_model(request.codexModel)
    settings["codexReasoningEffort"] = normalize_codex_reasoning_effort(request.codexReasoningEffort)
    save_app_settings(settings)
    log_server_event(
        "info",
        "codex-model-settings-updated",
        {
            "codexModel": settings["codexModel"],
            "codexReasoningEffort": settings["codexReasoningEffort"],
        },
    )
    return setting_payload()


@app.post("/api/settings/discord")
def save_discord_settings(request: DiscordSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["discord"] = normalize_discord_settings(base_model_payload(request))
    save_app_settings(settings)
    bridge_status = ABC_DISCORD_BRIDGE.apply_settings(settings) if ABC_DISCORD_BRIDGE is not None else {}
    log_server_event(
        "info",
        "discord-settings-updated",
        {
            "enabled": settings["discord"]["enabled"],
            "channelId": settings["discord"]["channelId"],
            "project": settings["discord"]["project"],
            "file": settings["discord"]["file"],
            "targetNodeId": settings["discord"]["targetNodeId"],
            "bridgeStatus": bridge_status,
        },
    )
    return setting_payload()


@app.get("/api/settings/discord/status")
def get_discord_status() -> dict[str, Any]:
    return ABC_DISCORD_BRIDGE.status() if ABC_DISCORD_BRIDGE is not None else {"running": False, "status": "unavailable"}


@app.post("/api/settings/title-style")
def save_title_style_settings(request: TitleStyleSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["titleFontFamily"] = normalize_title_font_family(request.titleFontFamily)
    settings["titleFontScale"] = clamp_title_font_scale(request.titleFontScale)
    settings["titleOutlineEnabled"] = bool(request.titleOutlineEnabled)
    settings["titleOutlineColor"] = normalize_hex_color(request.titleOutlineColor, "#ffffff")
    settings["titleOutlineWidth"] = clamp_title_outline_width(request.titleOutlineWidth)
    settings["titleShadowEnabled"] = bool(request.titleShadowEnabled)
    settings["titleShadowColor"] = normalize_hex_color(request.titleShadowColor, "#ffffff")
    settings["titleShadowBlur"] = clamp_title_shadow_blur(request.titleShadowBlur)
    settings["titleShadowX"] = clamp_title_shadow_offset(request.titleShadowX, 0.0)
    settings["titleShadowY"] = clamp_title_shadow_offset(request.titleShadowY, 1.0)
    save_app_settings(settings)
    log_server_event(
        "info",
        "title-style-settings-updated",
        {
            "font": settings["titleFontFamily"],
            "scale": settings["titleFontScale"],
            "outline": settings["titleOutlineEnabled"],
            "shadow": settings["titleShadowEnabled"],
        },
    )
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


def codex_workspace_root(project: str) -> Path:
    safe_project = STORE.safe_project_name(project)
    digest = hashlib.sha1(safe_project.encode("utf-8")).hexdigest()[:12]
    return (CODEX_WORKSPACE_ROOT / f"{safe_project}-{digest}").resolve()


def sync_codex_workspace(project: str) -> Path:
    source_root = STORE.project_root(project)
    workspace_root = codex_workspace_root(project)
    workspace_parent = CODEX_WORKSPACE_ROOT.resolve()
    if workspace_parent not in workspace_root.parents and workspace_root != workspace_parent:
        raise HTTPException(status_code=400, detail="Invalid Codex workspace path")
    workspace_root.mkdir(parents=True, exist_ok=True)
    ensure_project_scaffold(workspace_root)
    stale_config = workspace_root / ".codex" / "config.toml"
    if stale_config.exists():
        stale_config.unlink()

    for forbidden_name in (DEFAULT_FILE, "powan.db"):
        forbidden_path = workspace_root / forbidden_name
        if forbidden_path.exists():
            forbidden_path.unlink()

    (workspace_root / ".abc_canvas_workspace.json").write_text(
        json.dumps(
            {
                "project": STORE.safe_project_name(project),
                "realProjectRoot": str(source_root),
                "note": "Codex用の隔離作業場所です。ポワン状態はAPIツール経由で保存します。",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return workspace_root


def mark_codex_disconnected_safe(
    project: str,
    file: str,
    node_id: str,
    conversation_id: int | None,
    reason: str,
) -> None:
    try:
        STORE.mark_powan_codex_disconnected(
            project,
            file,
            node_id,
            conversation_id=conversation_id,
            reason=reason,
        )
    except Exception as exc:
        log_server_event(
            "error",
            "codex-disconnected-mark-failed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation_id,
                "reason": reason,
                "error": repr(exc),
            },
        )


def codex_result_already_running(result: Any) -> bool:
    return int(getattr(result, "returncode", 0) or 0) == 409 and "already running" in str(getattr(result, "stderr", "")).lower()


DEAD_CODEX_RUN_ERROR = "Codexプロセスが見つかりません。DBの作業中状態だけが残っていたため失敗にしました。"


def find_codex_pid_for_thread(thread_id: str) -> int | None:
    clean_thread_id = str(thread_id or "").strip()
    if not clean_thread_id or os.name != "nt":
        return None
    escaped_thread_id = clean_thread_id.replace("'", "''")
    command = (
        "$thread = '" + escaped_thread_id + "'; "
        "$matches = Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -like \"*$thread*\" -and "
        "($_.Name -ieq 'codex.exe' -or $_.Name -ieq 'node.exe' -or $_.Name -ieq 'cmd.exe') }; "
        "$preferred = $matches | Where-Object { $_.Name -ieq 'codex.exe' } | Select-Object -First 1; "
        "if (-not $preferred) { $preferred = $matches | Select-Object -First 1 }; "
        "if ($preferred) { $preferred.ProcessId }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return int(line)
        except ValueError:
            continue
    return None


def reconcile_running_agent_runs(
    project: str,
    file: str,
    *,
    node_id: str | None = None,
    conversation_id: int | None = None,
) -> list[dict[str, Any]]:
    safe_project = STORE.safe_project_name(project)
    safe_file = STORE.safe_powan_name(file)
    live_runs: list[dict[str, Any]] = []
    for run in STORE.list_running_agent_runs(project, file):
        run_node_id = str(run.get("powanId") or "")
        run_conversation_id = run.get("conversationId")
        if node_id and run_node_id != node_id:
            continue
        if conversation_id is not None and int(run_conversation_id or 0) != int(conversation_id):
            continue
        live_info = CODEX_BRIDGE.active_run_info(
            project=safe_project,
            document_name=safe_file,
            node_id=run_node_id,
            run_id=int(run["id"]),
        )
        if live_info is not None:
            next_run = {**run, "live": True}
            if live_info.get("pid") is not None:
                next_run["pid"] = live_info["pid"]
            next_run["processRunning"] = bool(live_info.get("processRunning"))
            live_runs.append(next_run)
            continue
        pid = run.get("pid")
        if pid is None:
            pid = find_codex_pid_for_thread(str(run.get("threadId") or ""))
            if pid is not None:
                STORE.set_agent_run_pid(project, int(run["id"]), int(pid))
        if pid is not None and CODEX_BRIDGE.is_pid_running(int(pid)):
            live_runs.append({**run, "pid": int(pid), "live": True, "processRunning": True})
            continue
        failed = STORE.fail_agent_run_if_running(project, int(run["id"]), DEAD_CODEX_RUN_ERROR)
        if failed is None:
            continue
        STORE.fail_child_command_dispatches_for_run(
            project,
            str(failed.get("documentName") or safe_file),
            str(failed.get("powanId") or run_node_id),
            int(failed["conversationId"]) if failed.get("conversationId") is not None else None,
            DEAD_CODEX_RUN_ERROR,
        )
        mark_codex_disconnected_safe(
            project,
            str(failed.get("documentName") or safe_file),
            str(failed.get("powanId") or run_node_id),
            int(failed["conversationId"]) if failed.get("conversationId") is not None else None,
            "codex-process-missing",
        )
        log_server_event(
            "warn",
            "codex-run-reconciled-dead",
            {
                "project": safe_project,
                "file": safe_file,
                "nodeId": failed.get("powanId") or run_node_id,
                "conversationId": failed.get("conversationId"),
                "runId": failed.get("id"),
            },
        )
    return live_runs


def live_conversation_payload(project: str, file: str, node_id: str, conversation_id: int | None = None) -> dict[str, Any]:
    if conversation_id is None:
        payload = STORE.list_conversation_messages(project, file, node_id)
    else:
        payload = STORE.conversation_messages_by_id(project, file, node_id, conversation_id)
    resolved_conversation_id = int(payload["conversationId"])
    live_runs = reconcile_running_agent_runs(
        project,
        file,
        node_id=node_id,
        conversation_id=resolved_conversation_id,
    )
    payload = STORE.conversation_messages_by_id(project, file, node_id, resolved_conversation_id)
    payload["activeRun"] = live_runs[0] if live_runs else None
    return payload


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
        "delegated": "委譲",
        "failed": "失敗",
        "cancelled": "キャンセル",
    }
    return f"{sender_label} -> {receiver_label} / {status_labels.get(status, status)}"


def limit_prompt_text(text: Any, limit: int = 12000) -> str:
    value = str(text or "")
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n... truncated {len(value) - limit} chars ..."


def incoming_kind_for_source(source: str) -> str:
    if source == "command-children":
        return "parent_command"
    if source == "command-child-return":
        return "child_replies"
    if source in {"origin-report-judgement", "origin-report-judgement-retry"}:
        return "origin_report_judgement"
    if source in {"origin-report-promoted", "origin-report-unmet"}:
        return "origin_report"
    return "operator_message"


def incoming_allowed_action(source: str, *, continue_after_child_replies: bool = False) -> str:
    if source in {"origin-report-judgement", "origin-report-judgement-retry"}:
        return "must_judge_origin_report"
    if source == "command-child-return" and not continue_after_child_replies:
        return "read_only"
    return "may_command_children"


def incoming_from_payload(source: str, sender_node_id: str | None, sender_label: str) -> dict[str, Any]:
    if source == "command-children":
        return {
            "kind": "parent_powan",
            "id": sender_node_id,
            "name": sender_label,
        }
    if source == "command-child-return":
        return {
            "kind": "child_powan_bundle",
            "id": sender_node_id,
            "name": sender_label,
        }
    if source in {"origin-report-judgement", "origin-report-judgement-retry", "origin-report-promoted", "origin-report-unmet"}:
        return {
            "kind": "origin_route",
            "id": sender_node_id,
            "name": sender_label,
        }
    return {
        "kind": "operator",
        "id": None,
        "name": "ユーザー",
    }


def incoming_system_instruction(kind: str, allowed_action: str) -> str:
    if kind == "parent_command":
        return "これは親ポワンからこのポワンへの命令です。from.kind と parentCommand を見て処理してください。"
    if kind == "child_replies":
        if allowed_action == "may_command_children":
            return "これは子ポワンから親ポワンへ戻った返答通知です。commandChildren.continueAfterChildReplies=true により、必要なら子返答後も command-children を続けて実行できます。"
        return "これは子ポワンから親ポワンへ戻った返答通知です。allowedAction=read_only の範囲で、返答内容の確認と要約だけを行ってください。"
    if kind == "origin_report_judgement":
        return "これは由来つき報告の判定です。requiredJudgement を読み、指定されたJSONだけを返してください。"
    if kind == "origin_report":
        return "これは由来つき作業の上流または下流から届いた報告です。originChain を維持して処理してください。"
    return "これはユーザーからこのポワンへの入力です。"


def build_incoming_message_payload(
    *,
    source: str,
    text: str,
    sender_node_id: str | None,
    sender_label: str,
    receiver_node_id: str,
    receiver_label: str,
    conversation_id: int,
    user_message_id: int | None,
    continue_after_child_replies: bool = False,
    command_children_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kind = incoming_kind_for_source(source)
    allowed_action = incoming_allowed_action(
        source,
        continue_after_child_replies=continue_after_child_replies,
    )
    payload: dict[str, Any] = {
        "kind": kind,
        "source": source,
        "from": incoming_from_payload(source, sender_node_id, sender_label),
        "to": {
            "kind": "powan",
            "id": receiver_node_id,
            "name": receiver_label,
            "conversationId": conversation_id,
            "messageId": user_message_id,
        },
        "operatorMessage": "",
        "parentCommand": "",
        "childReplies": [],
        "body": text,
        "allowedAction": allowed_action,
        "systemInstruction": incoming_system_instruction(kind, allowed_action),
    }
    if command_children_context is not None:
        payload["commandChildren"] = {
            **command_children_context,
            "continueAfterChildReplies": bool(continue_after_child_replies),
        }
    if kind == "parent_command":
        payload["parentCommand"] = text
    elif kind == "child_replies":
        payload["childReplies"] = []
    else:
        payload["operatorMessage"] = text
    return payload


def child_reply_payloads(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    for result in results:
        assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
        agent_run = result.get("agentRun") if isinstance(result.get("agentRun"), dict) else None
        replies.append(
            {
                "from": {
                    "kind": "child_powan",
                    "id": result.get("nodeId"),
                    "name": str(result.get("meaning") or "名前のないポワン"),
                },
                "status": str(result.get("status") or "unknown"),
                "conversationId": result.get("conversationId"),
                "dispatchSessionId": result.get("dispatchSessionId"),
                "dispatchId": result.get("dispatchId"),
                "assistantMessageId": assistant_message.get("id") if assistant_message else None,
                "agentRunId": agent_run.get("id") if agent_run else None,
                "text": limit_prompt_text((assistant_message or {}).get("text") or "", 12000),
                "error": limit_prompt_text(result.get("error") or "", 4000),
            }
        )
    return replies


def child_result_should_return_to_parent(result: dict[str, Any]) -> bool:
    if str(result.get("status") or "") == "delegated":
        return False
    if result.get("earlyCompleted") and str(result.get("earlyCompleteReason") or "") == "command_children_accepted":
        return False
    return True


def child_return_incoming_message(
    *,
    parent_id: str,
    parent_label: str,
    parent_conversation_id: int,
    parent_message_id: int | None,
    parent_text: str,
    results: list[dict[str, Any]],
    continue_after_child_replies: bool = False,
    dispatch_session_id: str = "",
) -> dict[str, Any]:
    payload = build_incoming_message_payload(
        source="command-child-return",
        text=parent_text,
        sender_node_id=str(results[0].get("nodeId") or "") if len(results) == 1 else None,
        sender_label="子ポワン一括返答",
        receiver_node_id=parent_id,
        receiver_label=parent_label,
        conversation_id=parent_conversation_id,
        user_message_id=parent_message_id,
        continue_after_child_replies=continue_after_child_replies,
        command_children_context={
            "dispatchSessionId": dispatch_session_id,
        },
    )
    payload["childReplies"] = child_reply_payloads(results)
    return payload


def normalize_origin_chain(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    chain: list[dict[str, Any]] = []
    for raw in value[:50]:
        if not isinstance(raw, dict):
            continue
        from_node = raw.get("from") if isinstance(raw.get("from"), dict) else {}
        to_node = raw.get("to") if isinstance(raw.get("to"), dict) else {}
        from_id = str(raw.get("fromId") or from_node.get("id") or "").strip()
        to_id = str(raw.get("toId") or to_node.get("id") or "").strip()
        if not from_id or not to_id:
            continue
        chain.append(
            {
                "schema": ORIGIN_CHAIN_SCHEMA,
                "fromId": from_id,
                "fromName": str(raw.get("fromName") or from_node.get("name") or "").strip(),
                "toId": to_id,
                "toName": str(raw.get("toName") or to_node.get("name") or "").strip(),
                "dispatchSessionId": str(raw.get("dispatchSessionId") or "").strip(),
                "dispatchId": raw.get("dispatchId"),
                "instruction": limit_prompt_text(raw.get("instruction") or "", 4000),
            }
        )
    return chain


def origin_hop(
    *,
    from_id: str,
    from_name: str,
    to_id: str,
    to_name: str,
    dispatch_session_id: str = "",
    dispatch_id: Any = None,
    instruction: str = "",
) -> dict[str, Any]:
    return {
        "schema": ORIGIN_CHAIN_SCHEMA,
        "fromId": str(from_id or "").strip(),
        "fromName": str(from_name or "").strip(),
        "toId": str(to_id or "").strip(),
        "toName": str(to_name or "").strip(),
        "dispatchSessionId": str(dispatch_session_id or "").strip(),
        "dispatchId": dispatch_id,
        "instruction": limit_prompt_text(instruction, 4000),
    }


def append_origin_hop(chain: Any, hop: dict[str, Any]) -> list[dict[str, Any]]:
    clean_chain = normalize_origin_chain(chain)
    if hop.get("fromId") and hop.get("toId"):
        clean_chain.append(hop)
    return clean_chain


def origin_upstream(chain: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not chain:
        return None
    hop = chain[-1]
    upstream_id = str(hop.get("fromId") or "").strip()
    if not upstream_id:
        return None
    return {
        "id": upstream_id,
        "name": str(hop.get("fromName") or "名前のないポワン").strip() or "名前のないポワン",
        "originChain": chain[:-1],
    }


def build_downstream_origin_reports(
    *,
    base_chain: list[dict[str, Any]],
    parent_id: str,
    parent_label: str,
    results: list[dict[str, Any]],
    dispatch_session_id: str,
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for result in results:
        child_id = str(result.get("nodeId") or "").strip()
        if not child_id:
            continue
        child_label = str(result.get("meaning") or "名前のないポワン").strip() or "名前のないポワン"
        assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
        report_text = str((assistant_message or {}).get("text") or result.get("error") or "").strip()
        report_chain = append_origin_hop(
            base_chain,
            origin_hop(
                from_id=parent_id,
                from_name=parent_label,
                to_id=child_id,
                to_name=child_label,
                dispatch_session_id=dispatch_session_id,
                dispatch_id=result.get("dispatchId"),
                instruction=str(result.get("instruction") or ""),
            ),
        )
        reports.append(
            {
                "childId": child_id,
                "childName": child_label,
                "status": str(result.get("status") or "unknown"),
                "conversationId": result.get("conversationId"),
                "dispatchSessionId": dispatch_session_id,
                "dispatchId": result.get("dispatchId"),
                "originChain": report_chain,
                "reportText": limit_prompt_text(report_text, 12000),
            }
        )
    return reports


def origin_judgement_template() -> dict[str, str]:
    return {
        "status": "achieved",
        "reason": "判定理由",
        "returnInstruction": "",
        "report": "人間にそのまま見せる自由文の報告本文",
    }


def origin_judgement_text(
    *,
    report_text: str,
    required_judgement: dict[str, Any],
) -> str:
    attempt = int(required_judgement.get("attempt") or 1)
    max_attempts = int(required_judgement.get("maxAttempts") or ORIGIN_JUDGEMENT_MAX_ATTEMPTS)
    validation_error = str(required_judgement.get("validationError") or "").strip()
    lines = [
        "由来つき報告が戻りました。",
        "この報告を読んで、達成なら上流へ、未達なら下流へ返します。",
        "",
        f"判定試行: {attempt}/{max_attempts}",
    ]
    if validation_error:
        lines.extend(["", "前回のJSONが不正でした。", validation_error])
    lines.extend(
        [
            "",
            "status は achieved か unmet のどちらかです。",
            "unmet の時だけ returnInstruction に下流への具体的な差し戻し指示を書いてください。",
            "report には人間が読むための自由文報告を書いてください。",
            "達成時の report には、何が終わったか、誰が何を担当したか、成果の要点を具体的に含めてください。",
            "未達時の report には、何が足りないか、誰へ何を戻すか、次に必要なことを具体的に含めてください。",
            "reason は短い判定根拠、report はそのまま会話に表示する本文です。",
            "",
            "返答は次のJSONだけにしてください。",
            json.dumps(origin_judgement_template(), ensure_ascii=False, indent=2),
            "",
            "--- 報告本文 ---",
            report_text.strip(),
        ]
    )
    return "\n".join(lines).strip()


def build_required_origin_judgement(
    *,
    judge_id: str,
    judge_label: str,
    origin_chain: list[dict[str, Any]],
    downstream_reports: list[dict[str, Any]],
    report_text: str,
    dispatch_session_id: str = "",
    attempt: int = 1,
    validation_error: str = "",
    previous_output: str = "",
) -> dict[str, Any]:
    return {
        "schema": ORIGIN_JUDGEMENT_SCHEMA,
        "required": True,
        "attempt": int(attempt),
        "maxAttempts": ORIGIN_JUDGEMENT_MAX_ATTEMPTS,
        "judge": {
            "id": judge_id,
            "name": judge_label,
        },
        "upstream": origin_upstream(origin_chain),
        "originChain": normalize_origin_chain(origin_chain),
        "downstreamReports": downstream_reports,
        "dispatchSessionId": dispatch_session_id,
        "reportText": limit_prompt_text(report_text, 16000),
        "validationError": validation_error,
        "previousOutput": limit_prompt_text(previous_output, 4000),
        "responseFormat": origin_judgement_template(),
    }


def attach_origin_judgement(
    incoming: dict[str, Any],
    *,
    required_judgement: dict[str, Any],
) -> dict[str, Any]:
    incoming["kind"] = "origin_report_judgement"
    incoming["allowedAction"] = "must_judge_origin_report"
    incoming["systemInstruction"] = incoming_system_instruction("origin_report_judgement", "must_judge_origin_report")
    incoming["originChain"] = normalize_origin_chain(required_judgement.get("originChain"))
    incoming["requiredJudgement"] = required_judgement
    return incoming


def strip_json_code_fence(text: str) -> str:
    clean = str(text or "").strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return clean


def parse_origin_judgement_response(text: str) -> tuple[dict[str, Any] | None, str]:
    clean = strip_json_code_fence(text)
    if not clean:
        return None, "返答が空です。"
    try:
        payload = json.loads(clean)
    except json.JSONDecodeError as exc:
        return None, f"JSONとして読めません: {exc}"
    if not isinstance(payload, dict):
        return None, "JSONの最上位がobjectではありません。"
    raw_status = str(payload.get("status") or payload.get("decision") or "").strip().lower()
    status_aliases = {
        "achieved": "achieved",
        "complete": "achieved",
        "completed": "achieved",
        "done": "achieved",
        "達成": "achieved",
        "完了": "achieved",
        "unmet": "unmet",
        "incomplete": "unmet",
        "not_achieved": "unmet",
        "not-achieved": "unmet",
        "未達": "unmet",
        "差し戻し": "unmet",
    }
    status = status_aliases.get(raw_status, "")
    if not status:
        return None, "status は achieved または unmet にしてください。"
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        return None, "reason が空です。"
    return_instruction = str(
        payload.get("returnInstruction")
        or payload.get("return_instruction")
        or payload.get("instruction")
        or ""
    ).strip()
    if status == "unmet" and not return_instruction:
        return None, "status が unmet の時は returnInstruction が必要です。"
    report = str(
        payload.get("report")
        or payload.get("humanReport")
        or payload.get("finalReport")
        or payload.get("message")
        or ""
    ).strip()
    if not report:
        return None, "report が空です。人間に見せる自由文報告を書いてください。"
    if len(report) < 20:
        return None, "report が短すぎます。成果や不足点を人間が読める自由文で具体的に書いてください。"
    if compact_origin_report_text(report, 10000) == compact_origin_report_text(reason, 10000):
        return None, "report は reason のコピーではなく、読ませるための具体的な報告本文にしてください。"
    return {
        "status": status,
        "reason": reason,
        "returnInstruction": return_instruction,
        "report": report,
        "raw": payload,
    }, ""


def compact_origin_report_text(text: Any, limit: int = 220) -> str:
    clean = " ".join(line.strip() for line in str(text or "").splitlines() if line.strip())
    if len(clean) <= limit:
        return clean
    return f"{clean[:limit]}..."


def origin_result_status_label(status: Any) -> str:
    value = str(status or "").strip().lower()
    labels = {
        "achieved": "達成",
        "completed": "完了",
        "complete": "完了",
        "done": "完了",
        "delegated": "委譲",
        "accepted": "受付",
        "unmet": "未達",
        "failed": "失敗",
        "cancelled": "キャンセル",
    }
    return labels.get(value, str(status or "不明"))


def render_origin_judgement_decision_message(
    *,
    decision: dict[str, Any],
    required_judgement: dict[str, Any],
    receiver_label: str,
) -> str:
    achieved = decision.get("status") == "achieved"
    title = "達成" if achieved else "未達"
    judge = required_judgement.get("judge") if isinstance(required_judgement.get("judge"), dict) else {}
    judge_label = str(judge.get("name") or receiver_label or "名前のないポワン").strip()
    upstream = required_judgement.get("upstream") if isinstance(required_judgement.get("upstream"), dict) else None
    downstream_reports = required_judgement.get("downstreamReports")
    reports = downstream_reports if isinstance(downstream_reports, list) else []
    report_text = str(decision.get("report") or "").strip()
    lines = [
        f"由来つき作業: {title}",
        "",
        f"判定者: {judge_label}",
    ]
    if achieved:
        upstream_label = str((upstream or {}).get("name") or "").strip()
        lines.append(f"上げ先: {upstream_label or 'ここで完了'}")
    else:
        return_targets = [
            str(report.get("childName") or report.get("childId") or "").strip()
            for report in reports
            if isinstance(report, dict)
        ]
        return_targets = [target for target in return_targets if target]
        lines.append(f"差し戻し先: {', '.join(return_targets) if return_targets else '下流ポワン'}")

    if report_text:
        lines.extend(["", "報告:", report_text])

    if reports:
        lines.extend(["", "下流からの返答:"])
        for report in reports[:10]:
            if not isinstance(report, dict):
                continue
            child_label = str(report.get("childName") or report.get("childId") or "名前のないポワン").strip()
            status_label = origin_result_status_label(report.get("status"))
            lines.append(f"- {child_label}: {status_label}")
            summary = compact_origin_report_text(report.get("reportText"), 260)
            if summary:
                lines.append(f"  {summary}")
        if len(reports) > 10:
            lines.append(f"- 他 {len(reports) - 10} 件")
    else:
        previous_report_text = compact_origin_report_text(required_judgement.get("reportText"), 320)
        lines.extend(["", "下流からの返答:", f"- {previous_report_text or '報告本文なし'}"])

    reason_label = "判定理由" if achieved else "未達理由"
    lines.extend(["", f"{reason_label}:", str(decision.get("reason") or "").strip()])
    return_instruction = str(decision.get("returnInstruction") or "").strip()
    if not achieved and return_instruction:
        lines.extend(["", "差し戻し指示:", return_instruction])
    return "\n".join(lines).strip()


def origin_judgement_assistant_display_text(
    *,
    raw_text: str,
    incoming_message: dict[str, Any],
    receiver_label: str,
) -> str:
    required = incoming_message.get("requiredJudgement") if isinstance(incoming_message.get("requiredJudgement"), dict) else {}
    if not required.get("required"):
        return raw_text
    decision, _ = parse_origin_judgement_response(raw_text)
    if not decision:
        return raw_text
    return render_origin_judgement_decision_message(
        decision=decision,
        required_judgement=required,
        receiver_label=receiver_label,
    )


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


def pending_codex_drain_key(project: str, file: str, node_id: str) -> str:
    return f"{STORE.safe_project_name(project)}\n{STORE.safe_powan_name(file)}\n{node_id}"


def render_pending_codex_message_bundle(items: list[dict[str, Any]]) -> str:
    if len(items) == 1:
        return str(items[0].get("text") or "")
    parts = []
    for index, item in enumerate(items, start=1):
        parts.append(
            "\n".join(
                [
                    f"## {index}. 未処理メッセージ",
                    f"messageId: {item.get('messageId')}",
                    f"source: {item.get('source') or 'unknown'}",
                    "",
                    str(item.get("text") or ""),
                ]
            )
        )
    return "\n\n".join(parts)


def build_pending_codex_incoming_message(
    *,
    node_id: str,
    receiver_label: str,
    conversation_id: int,
    text: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    first = items[0]
    first_payload = first.get("payload") if isinstance(first.get("payload"), dict) else {}
    if len(items) == 1 and isinstance(first_payload.get("requiredJudgement"), dict):
        incoming = dict(first_payload)
        incoming["body"] = text
        incoming["queuedMessages"] = [
            {
                "pendingId": first.get("id"),
                "messageId": first.get("messageId"),
                "source": first.get("source"),
                "senderId": first.get("senderId"),
                "senderLabel": first.get("senderLabel"),
            }
        ]
        return incoming
    continue_after_child_replies = any(
        bool((item.get("payload") or {}).get("commandChildren", {}).get("continueAfterChildReplies"))
        for item in items
    )
    incoming = build_incoming_message_payload(
        source="command-child-return",
        text=text,
        sender_node_id=str(first.get("senderId") or "") or None,
        sender_label=str(first.get("senderLabel") or "DB未処理メッセージ"),
        receiver_node_id=node_id,
        receiver_label=receiver_label,
        conversation_id=conversation_id,
        user_message_id=int(items[-1]["messageId"]) if items[-1].get("messageId") is not None else None,
        continue_after_child_replies=continue_after_child_replies,
        command_children_context={
            "pendingIds": [item.get("id") for item in items],
            "pendingMessageIds": [item.get("messageId") for item in items],
        },
    )
    child_replies: list[dict[str, Any]] = []
    for item in items:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        for reply in payload.get("childReplies") or []:
            if isinstance(reply, dict):
                child_replies.append(reply)
    incoming["childReplies"] = child_replies
    incoming["queuedMessages"] = [
        {
            "pendingId": item.get("id"),
            "messageId": item.get("messageId"),
            "source": item.get("source"),
            "senderId": item.get("senderId"),
            "senderLabel": item.get("senderLabel"),
        }
        for item in items
    ]
    return incoming


def pending_item_requires_origin_judgement(item: dict[str, Any]) -> bool:
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    required = payload.get("requiredJudgement") if isinstance(payload.get("requiredJudgement"), dict) else {}
    return bool(required.get("required"))


def queue_origin_judgement_message(
    *,
    project: str,
    file: str,
    judge_id: str,
    judge_label: str,
    sender_id: str | None,
    sender_label: str,
    report_text: str,
    required_judgement: dict[str, Any],
    source: str,
    reason: str,
) -> dict[str, Any]:
    conversation = STORE.active_conversation(project, file, judge_id)
    text = origin_judgement_text(
        report_text=report_text,
        required_judgement=required_judgement,
    )
    message = emit_conversation_event(
        project=project,
        file=file,
        node_id=judge_id,
        conversation_id=int(conversation["id"]),
        kind="origin_report_judgement",
        role="user",
        text=text,
        receiver_label=judge_label,
        source=source,
        metadata={
            "originSchema": ORIGIN_JUDGEMENT_SCHEMA,
            "originAttempt": required_judgement.get("attempt"),
            "originReason": reason,
        },
    )
    incoming = build_incoming_message_payload(
        source=source,
        text=text,
        sender_node_id=sender_id,
        sender_label=sender_label,
        receiver_node_id=judge_id,
        receiver_label=judge_label,
        conversation_id=int(conversation["id"]),
        user_message_id=int(message["id"]) if message.get("id") is not None else None,
    )
    attach_origin_judgement(incoming, required_judgement=required_judgement)
    STORE.queue_pending_codex_message(
        project,
        file,
        judge_id,
        int(conversation["id"]),
        int(message["id"]),
        source=source,
        sender_id=sender_id,
        sender_label=sender_label,
        payload=incoming,
    )
    schedule_pending_codex_drain(project, file, judge_id, reason=reason)
    log_server_event(
        "info",
        "origin-report-judgement-queued",
        {
            "console": True,
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "judgeId": judge_id,
            "judgeLabel": judge_label,
            "senderId": sender_id,
            "senderLabel": sender_label,
            "conversationId": int(conversation["id"]),
            "messageId": message.get("id"),
            "attempt": required_judgement.get("attempt"),
            "reason": reason,
            "upstream": required_judgement.get("upstream"),
            "downstreamCount": len(required_judgement.get("downstreamReports") or []),
        },
    )
    return {
        "conversation": conversation,
        "message": message,
        "incomingMessage": incoming,
    }


def queue_origin_judgement_retry(
    *,
    project: str,
    file: str,
    node_id: str,
    receiver_label: str,
    sender_id: str | None,
    sender_label: str,
    required_judgement: dict[str, Any],
    validation_error: str,
    previous_output: str,
) -> None:
    attempt = int(required_judgement.get("attempt") or 1) + 1
    max_attempts = int(required_judgement.get("maxAttempts") or ORIGIN_JUDGEMENT_MAX_ATTEMPTS)
    if attempt > max_attempts:
        conversation = STORE.active_conversation(project, file, node_id)
        emit_conversation_event(
            project=project,
            file=file,
            node_id=node_id,
            conversation_id=int(conversation["id"]),
            kind="origin_report_judgement_failed",
            role="system",
            text=f"由来報告の判定JSONが{max_attempts}回不正だったため停止しました。\n{validation_error}",
            receiver_label=receiver_label,
            source="origin-report-judgement",
            metadata={"originSchema": ORIGIN_JUDGEMENT_SCHEMA},
        )
        log_server_event(
            "error",
            "origin-report-judgement-retry-exhausted",
            {
                "console": True,
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "receiverLabel": receiver_label,
                "attempt": attempt - 1,
                "maxAttempts": max_attempts,
                "validationError": validation_error,
                "previousOutput": limit_prompt_text(previous_output, 1000),
            },
        )
        return
    retry_required = {
        **required_judgement,
        "attempt": attempt,
        "validationError": validation_error,
        "previousOutput": limit_prompt_text(previous_output, 4000),
    }
    queue_origin_judgement_message(
        project=project,
        file=file,
        judge_id=node_id,
        judge_label=receiver_label,
        sender_id=sender_id,
        sender_label=sender_label,
        report_text=str(required_judgement.get("reportText") or ""),
        required_judgement=retry_required,
        source="origin-report-judgement-retry",
        reason="origin-judgement-invalid-retry",
    )


def render_origin_promoted_report(
    *,
    judge_label: str,
    decision: dict[str, Any],
    report_text: str,
) -> str:
    decision_report = str(decision.get("report") or "").strip()
    lines = [
        f"{judge_label} が由来つき報告を達成として上流へ上げました。",
        "",
        "報告:",
        decision_report or "報告本文なし。",
        "",
        f"判定理由: {decision.get('reason') or ''}",
        "",
        "--- 下流からの報告 ---",
        report_text.strip(),
    ]
    return "\n".join(lines).strip()


def render_origin_unmet_instruction(
    *,
    judge_label: str,
    decision: dict[str, Any],
    report: dict[str, Any],
) -> str:
    lines = [
        f"上位ポワン「{judge_label}」から、由来つき作業の差し戻しです。",
        "",
        "--- 報告 ---",
        str(decision.get("report") or "").strip() or "報告本文なし。",
        "",
        "--- 差し戻し指示 ---",
        str(decision.get("returnInstruction") or "").strip(),
        "",
        "--- 未達理由 ---",
        str(decision.get("reason") or "").strip(),
    ]
    report_text = str(report.get("reportText") or "").strip()
    if report_text:
        lines.extend(["", "--- 直前の報告 ---", report_text])
    return "\n".join(lines).strip()


def queue_origin_worker_completion(
    *,
    project: str,
    file: str,
    worker_id: str,
    worker_label: str,
    origin_chain: list[dict[str, Any]],
    assistant_message: dict[str, Any],
    agent_run: dict[str, Any],
) -> None:
    full_chain = normalize_origin_chain(origin_chain)
    if not full_chain:
        return
    last_hop = full_chain[-1]
    upstream_id = str(last_hop.get("fromId") or "").strip()
    if not upstream_id:
        return
    document = STORE.load_document(project, file)
    upstream_label = powan_label_from_document(document, upstream_id)
    assistant_text = str(assistant_message.get("text") or "").strip()
    report_text = "\n".join(
        [
            f"下流ポワン「{worker_label}」から、差し戻し後の報告が戻りました。",
            "",
            assistant_text or "報告本文なし。",
        ]
    ).strip()
    downstream_reports = [
        {
            "childId": worker_id,
            "childName": worker_label,
            "status": "completed",
            "conversationId": assistant_message.get("conversationId"),
            "assistantMessageId": assistant_message.get("id"),
            "agentRunId": agent_run.get("id"),
            "originChain": full_chain,
            "reportText": limit_prompt_text(assistant_text, 12000),
        }
    ]
    required = build_required_origin_judgement(
        judge_id=upstream_id,
        judge_label=upstream_label,
        origin_chain=full_chain[:-1],
        downstream_reports=downstream_reports,
        report_text=report_text,
        dispatch_session_id=str(last_hop.get("dispatchSessionId") or ""),
    )
    queue_origin_judgement_message(
        project=project,
        file=file,
        judge_id=upstream_id,
        judge_label=upstream_label,
        sender_id=worker_id,
        sender_label=worker_label,
        report_text=report_text,
        required_judgement=required,
        source="origin-report-judgement",
        reason="origin-worker-complete",
    )
    log_server_event(
        "info",
        "origin-report-worker-completion-routed",
        {
            "console": True,
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "workerId": worker_id,
            "workerLabel": worker_label,
            "upstreamId": upstream_id,
            "upstreamLabel": upstream_label,
            "originDepth": len(full_chain),
        },
    )


def route_origin_achieved(
    *,
    project: str,
    file: str,
    node_id: str,
    receiver_label: str,
    required_judgement: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    origin_chain = normalize_origin_chain(required_judgement.get("originChain"))
    upstream = origin_upstream(origin_chain)
    report_text = str(required_judgement.get("reportText") or "").strip()
    if not upstream:
        conversation = STORE.active_conversation(project, file, node_id)
        resolved_lines = [
            "由来つき報告を達成として完了しました。",
            "",
            "報告:",
            str(decision.get("report") or "").strip() or "報告本文なし。",
            "",
            f"判定理由: {decision.get('reason') or ''}",
        ]
        emit_conversation_event(
            project=project,
            file=file,
            node_id=node_id,
            conversation_id=int(conversation["id"]),
            kind="origin_report_resolved",
            role="system",
            text="\n".join(resolved_lines).strip(),
            receiver_label=receiver_label,
            source="origin-report-judgement",
            metadata={"originSchema": ORIGIN_JUDGEMENT_SCHEMA},
        )
        log_server_event(
            "info",
            "origin-report-resolved-at-root",
            {
                "console": True,
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "receiverLabel": receiver_label,
                "reason": decision.get("reason"),
            },
        )
        return
    promoted_text = render_origin_promoted_report(
        judge_label=receiver_label,
        decision=decision,
        report_text=report_text,
    )
    upstream_id = str(upstream.get("id") or "")
    upstream_label = str(upstream.get("name") or powan_label_from_document(STORE.load_document(project, file), upstream_id))
    downstream_reports = [
        {
            "childId": node_id,
            "childName": receiver_label,
            "status": "achieved",
            "originChain": origin_chain,
            "reportText": limit_prompt_text(promoted_text, 12000),
        }
    ]
    required = build_required_origin_judgement(
        judge_id=upstream_id,
        judge_label=upstream_label,
        origin_chain=normalize_origin_chain(upstream.get("originChain")),
        downstream_reports=downstream_reports,
        report_text=promoted_text,
        dispatch_session_id=str(required_judgement.get("dispatchSessionId") or ""),
    )
    queue_origin_judgement_message(
        project=project,
        file=file,
        judge_id=upstream_id,
        judge_label=upstream_label,
        sender_id=node_id,
        sender_label=receiver_label,
        report_text=promoted_text,
        required_judgement=required,
        source="origin-report-judgement",
        reason="origin-judgement-achieved-promote",
    )
    log_server_event(
        "info",
        "origin-report-promoted",
        {
            "console": True,
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "fromId": node_id,
            "fromLabel": receiver_label,
            "toId": upstream_id,
            "toLabel": upstream_label,
            "originDepth": len(origin_chain),
            "reason": decision.get("reason"),
        },
    )


def route_origin_unmet(
    *,
    project: str,
    file: str,
    node_id: str,
    receiver_label: str,
    required_judgement: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    reports = required_judgement.get("downstreamReports")
    if not isinstance(reports, list) or not reports:
        log_server_event(
            "error",
            "origin-report-unmet-no-downstream",
            {
                "console": True,
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "receiverLabel": receiver_label,
                "requiredJudgement": required_judgement,
            },
        )
        return
    document = STORE.load_document(project, file)
    queued = 0
    for report in reports:
        if not isinstance(report, dict):
            continue
        child_id = str(report.get("childId") or "").strip()
        if not child_id:
            continue
        child_label = str(report.get("childName") or powan_label_from_document(document, child_id)).strip() or "名前のないポワン"
        origin_chain = normalize_origin_chain(report.get("originChain"))
        text = render_origin_unmet_instruction(
            judge_label=receiver_label,
            decision=decision,
            report=report,
        )
        conversation = STORE.active_conversation(project, file, child_id)
        message = emit_conversation_event(
            project=project,
            file=file,
            node_id=child_id,
            conversation_id=int(conversation["id"]),
            kind="origin_report_unmet",
            role="user",
            text=text,
            receiver_label=child_label,
            source="origin-report-unmet",
            metadata={
                "originSchema": ORIGIN_JUDGEMENT_SCHEMA,
                "judgeId": node_id,
                "judgeLabel": receiver_label,
            },
        )
        incoming = build_incoming_message_payload(
            source="origin-report-unmet",
            text=text,
            sender_node_id=node_id,
            sender_label=receiver_label,
            receiver_node_id=child_id,
            receiver_label=child_label,
            conversation_id=int(conversation["id"]),
            user_message_id=int(message["id"]) if message.get("id") is not None else None,
        )
        incoming["originChain"] = origin_chain
        incoming["originRoute"] = {
            "kind": "unmet_return",
            "reportBackOnComplete": True,
            "originChain": origin_chain,
            "judge": {
                "id": node_id,
                "name": receiver_label,
            },
            "reason": decision.get("reason"),
        }
        STORE.queue_pending_codex_message(
            project,
            file,
            child_id,
            int(conversation["id"]),
            int(message["id"]),
            source="origin-report-unmet",
            sender_id=node_id,
            sender_label=receiver_label,
            payload=incoming,
        )
        schedule_pending_codex_drain(project, file, child_id, reason="origin-judgement-unmet-return")
        queued += 1
    log_server_event(
        "info",
        "origin-report-unmet-routed",
        {
            "console": True,
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "receiverLabel": receiver_label,
            "queued": queued,
            "reason": decision.get("reason"),
        },
    )


def handle_origin_judgement_result(
    *,
    project: str,
    file: str,
    node_id: str,
    receiver_label: str,
    group: list[dict[str, Any]],
    incoming_message: dict[str, Any],
    result: dict[str, Any],
) -> None:
    required = incoming_message.get("requiredJudgement") if isinstance(incoming_message.get("requiredJudgement"), dict) else {}
    if not required.get("required"):
        return
    assistant = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else {}
    assistant_text = str(result.get("assistantRawText") or (assistant or {}).get("text") or "").strip()
    decision, validation_error = parse_origin_judgement_response(assistant_text)
    sender_id = str(group[0].get("senderId") or "") or None
    sender_label = str(group[0].get("senderLabel") or "由来報告")
    if not decision:
        queue_origin_judgement_retry(
            project=project,
            file=file,
            node_id=node_id,
            receiver_label=receiver_label,
            sender_id=sender_id,
            sender_label=sender_label,
            required_judgement=required,
            validation_error=validation_error,
            previous_output=assistant_text,
        )
        return
    log_server_event(
        "info",
        "origin-report-judgement-accepted",
        {
            "console": True,
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "receiverLabel": receiver_label,
            "status": decision.get("status"),
            "reason": decision.get("reason"),
            "pendingIds": [item.get("id") for item in group],
        },
    )
    if decision["status"] == "achieved":
        route_origin_achieved(
            project=project,
            file=file,
            node_id=node_id,
            receiver_label=receiver_label,
            required_judgement=required,
            decision=decision,
        )
    else:
        route_origin_unmet(
            project=project,
            file=file,
            node_id=node_id,
            receiver_label=receiver_label,
            required_judgement=required,
            decision=decision,
        )


def schedule_pending_codex_drain(project: str, file: str, node_id: str, reason: str = "pending-codex-drain") -> None:
    key = pending_codex_drain_key(project, file, node_id)
    with PENDING_CODEX_DRAIN_LOCK:
        if key in PENDING_CODEX_DRAIN_KEYS:
            return
        PENDING_CODEX_DRAIN_KEYS.add(key)
    threading.Thread(
        target=drain_pending_codex_messages,
        args=(project, file, node_id, key, reason),
        name=f"abc-pending-codex-{node_id}",
        daemon=True,
    ).start()


def schedule_all_pending_codex_drains(reason: str = "pending-codex-drain") -> int:
    targets = STORE.list_pending_codex_message_targets()
    for target in targets:
        schedule_pending_codex_drain(
            str(target["project"]),
            str(target["documentName"]),
            str(target["powanId"]),
            reason=reason,
        )
    if targets:
        log_server_event(
            "info",
            "pending-codex-drains-scheduled",
            {
                "console": True,
                "reason": reason,
                "targetCount": len(targets),
                "messageCount": sum(int(target.get("count") or 0) for target in targets),
            },
        )
    return len(targets)


def drain_pending_codex_messages(project: str, file: str, node_id: str, drain_key: str, reason: str) -> None:
    try:
        while True:
            if reconcile_running_agent_runs(project, file, node_id=node_id):
                time.sleep(1)
                continue
            items = STORE.claim_pending_codex_messages(project, file, node_id, limit=20)
            if not items:
                return
            groups: dict[int, list[dict[str, Any]]] = {}
            for item in items:
                groups.setdefault(int(item["conversationId"]), []).append(item)
            for conversation_id, group in groups.items():
                if any(pending_item_requires_origin_judgement(item) for item in group):
                    origin_items = [item for item in group if pending_item_requires_origin_judgement(item)]
                    process_item = origin_items[0]
                    requeue_ids = [
                        int(item["id"])
                        for item in group
                        if int(item["id"]) != int(process_item["id"])
                    ]
                    if requeue_ids:
                        STORE.finish_pending_codex_messages(
                            project,
                            requeue_ids,
                            "pending",
                            error_text="waiting for origin judgement item to finish",
                        )
                    group = [process_item]
                    conversation_id = int(process_item["conversationId"])
                pending_ids = [int(item["id"]) for item in group]
                receiver_label = powan_label_from_document(STORE.load_document(project, file), node_id)
                text = render_pending_codex_message_bundle(group)
                required_for_text = (
                    (group[0].get("payload") or {}).get("requiredJudgement")
                    if isinstance(group[0].get("payload"), dict)
                    else None
                )
                if isinstance(required_for_text, dict):
                    text = origin_judgement_text(
                        report_text=str(required_for_text.get("reportText") or text),
                        required_judgement=required_for_text,
                    )
                pre_message = {
                    "id": int(group[-1]["messageId"]),
                    "conversationId": int(conversation_id),
                    "role": group[-1].get("role") or "user",
                    "text": group[-1].get("text") or "",
                    "createdAt": group[-1].get("messageCreatedAt") or group[-1].get("createdAt") or "",
                }
                incoming_message = build_pending_codex_incoming_message(
                    node_id=node_id,
                    receiver_label=receiver_label,
                    conversation_id=int(conversation_id),
                    text=text,
                    items=group,
                )
                run_source = str(group[0].get("source") or "command-child-return")
                log_server_event(
                    "info",
                    "pending-codex-messages-dispatch",
                    {
                        "console": True,
                        "project": STORE.safe_project_name(project),
                        "file": STORE.safe_powan_name(file),
                        "nodeId": node_id,
                        "conversationId": int(conversation_id),
                        "count": len(group),
                        "pendingIds": pending_ids,
                        "reason": reason,
                    },
                )
                try:
                    result = run_powan_codex_message(
                        node_id,
                        project=project,
                        file=file,
                        text=text,
                        include_meaning_tree=False,
                        include_direct_child_code=False,
                        attachments=[],
                        source=run_source,
                        sender_node_id=str(group[0].get("senderId") or "") or None,
                        sender_label_override=str(group[0].get("senderLabel") or "DB未処理メッセージ"),
                        pre_appended_user_message=pre_message,
                        incoming_message=incoming_message,
                    )
                except HTTPException as exc:
                    if exc.status_code == 409:
                        STORE.finish_pending_codex_messages(project, pending_ids, "pending", error_text=str(exc.detail))
                        time.sleep(1)
                        break
                    STORE.finish_pending_codex_messages(project, pending_ids, "failed", error_text=str(exc.detail))
                except Exception as exc:
                    STORE.finish_pending_codex_messages(project, pending_ids, "failed", error_text=repr(exc))
                else:
                    if isinstance(incoming_message.get("requiredJudgement"), dict):
                        handle_origin_judgement_result(
                            project=project,
                            file=file,
                            node_id=node_id,
                            receiver_label=receiver_label,
                            group=group,
                            incoming_message=incoming_message,
                            result=result,
                        )
                    STORE.finish_pending_codex_messages(project, pending_ids, "processed")
    finally:
        with PENDING_CODEX_DRAIN_LOCK:
            PENDING_CODEX_DRAIN_KEYS.discard(drain_key)


def short_codex_command(command: str) -> str:
    clean = " ".join(str(command or "").split())
    if len(clean) <= 220:
        return clean
    return f"{clean[:220]}..."


def is_child_command_execution(command: str) -> bool:
    clean = str(command or "")
    return (
        "command-children" in clean
        or '"instructions"' in clean
        or '\\"instructions\\"' in clean
    )


def codex_event_progress_text(event: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "").strip()
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    item_type = str(item.get("type") or "").strip()
    if event_type == "item.started" and item_type == "command_execution":
        raw_command = str(item.get("command") or "")
        command = short_codex_command(raw_command)
        if is_child_command_execution(raw_command):
            return "子ポワンへの指示を送信中..."
        return f"コマンド開始: `{compact_console_text(command, 30)}`" if command else "コマンド開始"
    if event_type == "item.completed" and item_type == "command_execution":
        raw_command = str(item.get("command") or "")
        command = short_codex_command(raw_command)
        exit_code = item.get("exit_code")
        output = str(item.get("aggregated_output") or "").strip()
        if output.startswith("{"):
            try:
                payload = json.loads(output)
                result = payload.get("result") if isinstance(payload, dict) else None
                if isinstance(result, dict) and ("sent" in result or "skipped" in result or "dispatchSessionId" in result):
                    sent = result.get("sent")
                    skipped = result.get("skipped")
                    failed = result.get("failed")
                    status = result.get("status")
                    dispatch_session_id = result.get("dispatchSessionId")
                    sent_children = result.get("sentChildren") if isinstance(result.get("sentChildren"), list) else []
                    sent_names = [
                        str(child.get("title") or child.get("childId") or "").strip()
                        for child in sent_children
                        if isinstance(child, dict)
                    ]
                    lines = [f"子ポワンへの指示送信: {status or 'accepted'}"]
                    if sent is not None:
                        lines.append(f"送信: {sent}件")
                    if skipped is not None:
                        lines.append(f"対象外: {skipped}件")
                    if failed is not None:
                        lines.append(f"失敗: {failed}件")
                    if sent_names:
                        lines.append(f"送信先: {', '.join(name for name in sent_names if name)}")
                    if dispatch_session_id:
                        lines.append(f"一括指示ID: {dispatch_session_id}")
                    return "\n".join(lines)
            except json.JSONDecodeError:
                pass
        head = "コマンド完了"
        if exit_code is not None:
            head += f" exit={exit_code}"
        if is_child_command_execution(raw_command):
            return f"子ポワンへの指示送信完了 exit={exit_code}"
        if command:
            head += f": `{compact_console_text(command, 30)}`"
        if output:
            return f"{head}\n出力: {compact_console_text(output, 30)}"
        return head
    if event_type in {"item.started", "item.completed"} and item_type == "file_change":
        changes = item.get("changes") if isinstance(item.get("changes"), list) else []
        parts: list[str] = []
        for change in changes[:5]:
            if not isinstance(change, dict):
                continue
            path = str(change.get("path") or "").strip()
            kind = str(change.get("kind") or "").strip()
            if path:
                parts.append(f"{kind or 'change'} {path}")
        status = "開始" if event_type == "item.started" else "完了"
        return f"ファイル変更{status}: " + (", ".join(parts) if parts else "詳細なし")
    if event_type == "turn.completed":
        return "Codexターン完了"
    return ""


def conversation_event_should_discord(kind: str, source: str = "") -> bool:
    if source == "discord" and kind == "assistant_reply":
        return False
    return kind in {
        "assistant_reply",
        "codex_progress",
        "child_command_sent",
        "child_report_returned",
        "child_report_summary",
    }


def emit_conversation_event(
    *,
    project: str,
    file: str,
    node_id: str,
    conversation_id: int,
    kind: str,
    role: str,
    text: str,
    receiver_label: str,
    source: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean = str(text or "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Message text is required")
    message = STORE.append_conversation_message_to_conversation(
        project,
        file,
        node_id,
        int(conversation_id),
        role,
        clean,
    )
    payload = {
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "nodeId": node_id,
        "conversationId": int(conversation_id),
        "messageId": message.get("id"),
        "kind": kind,
        "role": role,
        "source": source,
        "messageLength": len(clean),
        **(metadata or {}),
    }
    log_server_event("info", "conversation-event-emitted", payload)
    if conversation_event_should_discord(kind, source=source):
        fanout_powan_conversation_text_to_discord(
            project=project,
            file=file,
            node_id=node_id,
            receiver_label=receiver_label,
            text=clean,
            reason=f"conversation-event:{kind}",
        )
    return message


def create_codex_progress_callback(
    *,
    project: str,
    file: str,
    node_id: str,
    receiver_label: str,
    conversation_id: int,
) -> Callable[[dict[str, Any]], None]:
    lock = threading.RLock()
    pending_agent_text = ""

    def append_progress(text: str) -> None:
        clean = str(text or "").strip()
        if not clean:
            return
        message = emit_conversation_event(
            project=project,
            file=file,
            node_id=node_id,
            conversation_id=int(conversation_id),
            kind="codex_progress",
            role="system",
            text=clean,
            receiver_label=receiver_label,
            source="codex-progress",
        )
        log_server_event(
            "info",
            "codex-progress-message-appended",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": int(conversation_id),
                "messageId": message.get("id"),
                "messageLength": len(clean),
            },
        )

    def flush_pending_agent() -> None:
        nonlocal pending_agent_text
        if pending_agent_text:
            append_progress(pending_agent_text)
            pending_agent_text = ""

    def callback(event: dict[str, Any]) -> None:
        nonlocal pending_agent_text
        if not isinstance(event, dict):
            return
        event_type = str(event.get("type") or "").strip()
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        item_type = str(item.get("type") or "").strip()
        with lock:
            if event_type == "item.completed" and item_type == "agent_message":
                pending_agent_text = str(item.get("text") or "").strip()
                return
            if event_type == "turn.completed":
                pending_agent_text = ""
                progress = codex_event_progress_text(event)
                if progress:
                    append_progress(progress)
                return
            flush_pending_agent()
            progress = codex_event_progress_text(event)
            if progress:
                append_progress(progress)

    return callback


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
    sender_label_override: str | None = None,
    pre_appended_user_message: dict[str, Any] | None = None,
    incoming_message: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document = STORE.load_document(project, file)
    if not any(str(node.get("id")) == node_id for node in document.get("nodes") or []):
        raise HTTPException(status_code=404, detail="Powan not found")
    receiver_label = powan_label_from_document(document, node_id)
    sender_label = (
        sender_label_override
        or (powan_label_from_document(document, sender_node_id) if sender_node_id else "ユーザー")
    )
    materialized_attachments = materialize_conversation_attachments(project, attachments or [])
    if pre_appended_user_message is not None:
        user_message = pre_appended_user_message
        conversation_id = int(user_message.get("conversationId") or 0)
        if conversation_id <= 0:
            raise HTTPException(status_code=500, detail="Pre-appended user message is missing conversationId")
        conversation_payload = STORE.conversation_messages_by_id(project, file, node_id, conversation_id)
        conversation = conversation_payload["conversation"]
        messages = conversation_payload["messages"]
    else:
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
        log_server_event(
            "info",
            "powan-user-message-appended",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "messageId": user_message.get("id"),
                "source": source,
                "senderNodeId": sender_node_id,
                "messageLength": len(text.strip()),
            },
        )
        messages = STORE.list_conversation_messages(project, file, node_id)["messages"]
    incoming_message_payload = incoming_message or build_incoming_message_payload(
        source=source,
        text=text,
        sender_node_id=sender_node_id,
        sender_label=sender_label,
        receiver_node_id=node_id,
        receiver_label=receiver_label,
        conversation_id=int(conversation["id"]),
        user_message_id=int(user_message["id"]) if user_message.get("id") is not None else None,
    )
    project_root_path = sync_codex_workspace(project)
    settings = load_app_settings()
    requested_codex_sandbox = normalize_codex_sandbox(settings.get("codexSandbox"))
    codex_sandbox = "workspace-write" if requested_codex_sandbox == "danger-full-access" else requested_codex_sandbox
    codex_model = normalize_codex_model(settings.get("codexModel"))
    codex_reasoning_effort = normalize_codex_reasoning_effort(settings.get("codexReasoningEffort"))
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
            "requestedCodexSandbox": requested_codex_sandbox,
            "codexModel": codex_model,
            "codexReasoningEffort": codex_reasoning_effort,
            "codexWorkspace": str(project_root_path),
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
            "requestedCodexSandbox": requested_codex_sandbox,
            "codexModel": codex_model,
            "codexReasoningEffort": codex_reasoning_effort,
            "includeDirectChildCode": bool(include_direct_child_code),
        },
    )
    run_payload = {
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "nodeId": node_id,
        "conversationId": conversation["id"],
        "threadId": conversation.get("codexThreadId"),
        "source": source,
        "userText": text,
        "includeMeaningTree": bool(include_meaning_tree),
        "includeDirectChildCode": bool(include_direct_child_code),
        "attachmentCount": len(materialized_attachments),
        "codexSandbox": codex_sandbox,
        "codexModel": codex_model,
        "codexReasoningEffort": codex_reasoning_effort,
        "incomingKind": incoming_message_payload.get("kind"),
        "incomingFrom": incoming_message_payload.get("from"),
        "allowedAction": incoming_message_payload.get("allowedAction"),
        "commandChildren": incoming_message_payload.get("commandChildren"),
        "originDepth": len(normalize_origin_chain(incoming_message_payload.get("originChain"))),
        "requiresOriginJudgement": bool(
            isinstance(incoming_message_payload.get("requiredJudgement"), dict)
            and incoming_message_payload.get("requiredJudgement", {}).get("required")
        ),
    }
    agent_run = STORE.start_agent_run(project, conversation["id"], node_id, run_payload)
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
            incoming_message=incoming_message_payload,
            include_meaning_tree=bool(include_meaning_tree),
            include_direct_child_code=bool(include_direct_child_code),
            attachments=materialized_attachments,
            codex_sandbox=codex_sandbox,
            codex_model=codex_model,
            codex_reasoning_effort=codex_reasoning_effort,
            agent_run_id=int(agent_run["id"]),
            on_process_started=lambda pid: STORE.set_agent_run_pid(project, int(agent_run["id"]), int(pid)),
            on_event=create_codex_progress_callback(
                project=project,
                file=file,
                node_id=node_id,
                receiver_label=receiver_label,
                conversation_id=int(conversation["id"]),
            ),
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
        STORE.finish_agent_run(
            project,
            agent_run["id"],
            "failed",
            {
                **run_payload,
                "crashed": True,
            },
            error_text=detail,
        )
        mark_codex_disconnected_safe(project, file, node_id, int(conversation["id"]), "codex-exec-crashed")
        raise HTTPException(status_code=502, detail=detail) from exc
    if result.thread_id and result.thread_id != conversation.get("codexThreadId"):
        STORE.set_conversation_codex_thread_id(project, conversation["id"], result.thread_id)
    run_payload = {
        **run_payload,
        "threadId": result.thread_id,
        "resumed": result.resumed,
        "command": result.command,
        "durationMs": result.duration_ms,
        "earlyCompleted": bool(result.early_completed),
        "earlyCompleteReason": result.early_complete_reason,
    }
    if result.cancelled:
        agent_run = STORE.finish_agent_run(
            project,
            agent_run["id"],
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
        schedule_pending_codex_drain(project, file, node_id, reason="codex-run-cancelled")
        return {
            "conversationId": conversation["id"],
            "codexThreadId": result.thread_id,
            "cancelled": True,
            "earlyCompleted": bool(result.early_completed),
            "earlyCompleteReason": result.early_complete_reason,
            "userMessage": user_message,
            "assistantMessage": None,
            "agentRun": agent_run,
        }
    if result.returncode != 0 or not result.text:
        STORE.finish_agent_run(
            project,
            agent_run["id"],
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
        if codex_result_already_running(result):
            raise HTTPException(status_code=409, detail="Codex exec already running for this powan")
        mark_codex_disconnected_safe(project, file, node_id, int(conversation["id"]), "codex-exec-failed")
        raise HTTPException(status_code=502, detail="Codex exec failed")
    agent_run = STORE.finish_agent_run(
        project,
        agent_run["id"],
        "completed",
        run_payload,
        output_text=result.text,
        error_text=result.stderr[-4000:],
    )
    assistant_display_text = origin_judgement_assistant_display_text(
        raw_text=result.text,
        incoming_message=incoming_message_payload,
        receiver_label=receiver_label,
    )
    assistant_message = emit_conversation_event(
        project=project,
        file=file,
        node_id=node_id,
        conversation_id=int(conversation["id"]),
        kind="assistant_reply",
        role="assistant",
        text=assistant_display_text,
        receiver_label=receiver_label,
        source=source,
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
            "displayLength": len(assistant_display_text),
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
            "displayLength": len(assistant_display_text),
        },
    )
    origin_route = incoming_message_payload.get("originRoute") if isinstance(incoming_message_payload.get("originRoute"), dict) else {}
    if origin_route.get("reportBackOnComplete") and not result.early_completed:
        queue_origin_worker_completion(
            project=project,
            file=file,
            worker_id=node_id,
            worker_label=receiver_label,
            origin_chain=normalize_origin_chain(origin_route.get("originChain") or incoming_message_payload.get("originChain")),
            assistant_message=assistant_message,
            agent_run=agent_run,
        )
    schedule_pending_codex_drain(project, file, node_id, reason="codex-run-completed")
    return {
        "conversationId": conversation["id"],
        "codexThreadId": result.thread_id,
        "earlyCompleted": bool(result.early_completed),
        "earlyCompleteReason": result.early_complete_reason,
        "assistantRawText": result.text,
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


def resolve_discord_project(project: str) -> str:
    clean = str(project or "").strip()
    if clean:
        return STORE.safe_project_name(clean)
    raise RuntimeError("Discord project is required")


def resolve_discord_target_powan(payload: dict[str, Any]) -> tuple[str, str, str, str]:
    project = resolve_discord_project(str(payload.get("project") or ""))
    file = STORE.safe_powan_name(str(payload.get("file") or DEFAULT_FILE))
    document = STORE.load_document(project, file)
    target_node_id = str(payload.get("targetNodeId") or "").strip()
    if target_node_id:
        target_node = document_node(document, target_node_id)
    else:
        roots = [node for node in document_nodes(document) if not node.get("parent")]
        if not roots:
            raise RuntimeError("Discord target powan is missing")
        target_node = roots[0]
        target_node_id = str(target_node.get("id") or "")
    if not target_node_id:
        raise RuntimeError("Discord target powan id is missing")
    return project, file, target_node_id, powan_label(target_node)


def discord_target_matches_powan(project: str, file: str, node_id: str) -> bool:
    settings = load_app_settings()
    discord_settings = dict(settings.get("discord") or {})
    if not bool(discord_settings.get("enabled")):
        return False
    try:
        target_project, target_file, target_node_id, _target_label = resolve_discord_target_powan(discord_settings)
    except Exception:
        return False
    return (
        STORE.safe_project_name(project) == target_project
        and STORE.safe_powan_name(file) == target_file
        and str(node_id) == str(target_node_id)
    )


def fanout_powan_conversation_text_to_discord(
    *,
    project: str,
    file: str,
    node_id: str,
    receiver_label: str,
    text: str,
    reason: str,
) -> None:
    clean = str(text or "").strip()
    if not clean or ABC_DISCORD_BRIDGE is None:
        return
    if not discord_target_matches_powan(project, file, node_id):
        return
    result = ABC_DISCORD_BRIDGE.send_configured_message(
        f"**{receiver_label}**\n{clean}".strip(),
        reason=reason,
    )
    log_server_event(
        "info" if result.get("sent") else "warn",
        "discord-fanout-conversation-event",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "reason": reason,
            **result,
        },
    )


def handle_discord_powan_message(payload: dict[str, Any]) -> dict[str, Any]:
    project, file, target_node_id, target_label = resolve_discord_target_powan(payload)
    content = str(payload.get("content") or "").strip()
    if not content:
        return {"ok": True, "reply": "", "displayName": target_label}
    if content.casefold() == "/cancel":
        result = CODEX_BRIDGE.cancel(
            project=project,
            document_name=file,
            node_id=target_node_id,
        )
        log_server_event(
            "info",
            "discord-codex-cancel",
            {
                "project": project,
                "file": file,
                "nodeId": target_node_id,
                "channelId": str(payload.get("channelId") or ""),
                "messageId": str(payload.get("messageId") or ""),
                **result,
            },
        )
        if result.get("cancelled"):
            reply = f"{target_label} の作業をキャンセルしました。"
        elif result.get("running"):
            reply = f"{target_label} のキャンセルを試しましたが止められませんでした。"
        else:
            reply = f"{target_label} は今作業していません。"
        return {
            "ok": True,
            "reply": reply,
            "displayName": target_label,
            "cancelled": bool(result.get("cancelled")),
            "running": bool(result.get("running")),
        }
    author_name = str(payload.get("authorName") or "Discord user")
    author_id = str(payload.get("authorId") or "")
    channel_id = str(payload.get("channelId") or "")
    message_id = str(payload.get("messageId") or "")
    incoming_message = {
        "kind": "operator_message",
        "source": "discord",
        "from": {
            "kind": "discord_user",
            "id": author_id,
            "name": author_name,
        },
        "to": {
            "kind": "powan",
            "id": target_node_id,
            "name": target_label,
        },
        "operatorMessage": content,
        "parentCommand": "",
        "childReplies": [],
        "body": content,
        "allowedAction": "may_command_children",
        "systemInstruction": "これはDiscordからこのポワンへの入力です。from.kind と本文を見て返答してください。",
        "discord": {
            "channelId": channel_id,
            "messageId": message_id,
        },
    }
    result = run_powan_codex_message(
        target_node_id,
        project=project,
        file=file,
        text=content,
        include_meaning_tree=False,
        include_direct_child_code=False,
        attachments=[],
        source="discord",
        sender_node_id=None,
        sender_label_override=author_name,
        incoming_message=incoming_message,
    )
    assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
    return {
        "ok": True,
        "reply": str((assistant_message or {}).get("text") or ""),
        "displayName": target_label,
        "conversationId": result.get("conversationId"),
        "agentRunId": (result.get("agentRun") or {}).get("id") if isinstance(result.get("agentRun"), dict) else None,
    }


ABC_DISCORD_BRIDGE = AbcDiscordBridge(
    root_dir=APP_ROOT,
    log_event=log_server_event,
    message_handler=handle_discord_powan_message,
)


@app.on_event("startup")
def start_discord_bridge() -> None:
    schedule_all_pending_codex_drains(reason="server-startup")
    if ABC_DISCORD_BRIDGE is None:
        return
    ABC_DISCORD_BRIDGE.apply_settings(load_app_settings())


@app.on_event("shutdown")
def stop_discord_bridge() -> None:
    if ABC_DISCORD_BRIDGE is not None:
        ABC_DISCORD_BRIDGE.stop("server-shutdown")


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


def render_parent_child_command_log(
    *,
    parent_label: str,
    child_label: str,
    instruction: str,
    rendered_text: str,
    dispatch_session_id: str,
    dispatch_id: Any,
) -> str:
    lines = [
        f"親ポワン「{parent_label}」から、子ポワン「{child_label}」へ指示を送りました。",
        "",
        f"一括指示ID: {dispatch_session_id}",
    ]
    if dispatch_id is not None:
        lines.append(f"送信ID: {dispatch_id}")
    clean_instruction = str(instruction or "").strip()
    clean_rendered = str(rendered_text or "").strip()
    if clean_instruction:
        lines.extend(["", "--- 指示 ---", clean_instruction])
    elif clean_rendered:
        lines.extend(["", "--- 指示 ---", clean_rendered])
    return "\n".join(lines).strip()


def render_child_parent_return_log(parent_label: str, result: dict[str, Any]) -> str:
    child_label = str(result.get("meaning") or "名前のないポワン").strip() or "名前のないポワン"
    status = str(result.get("status") or "").strip() or "unknown"
    dispatch_session_id = str(result.get("dispatchSessionId") or "").strip()
    dispatch_id = result.get("dispatchId")
    assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
    reply_text = str((assistant_message or {}).get("text") or "").strip()
    error_text = str(result.get("error") or "").strip()
    lines = [
        f"子ポワン「{child_label}」から、親ポワン「{parent_label}」へ報告しました。",
        "",
        f"状態: {status}",
    ]
    if dispatch_session_id:
        lines.append(f"一括指示ID: {dispatch_session_id}")
    if dispatch_id is not None:
        lines.append(f"送信ID: {dispatch_id}")
    if reply_text:
        lines.extend(["", "--- 親へ返した報告 ---", reply_text])
    elif error_text:
        lines.extend(["", "--- エラー ---", error_text])
    else:
        lines.extend(["", "報告本文はありません。"])
    return "\n".join(lines).strip()


def render_child_return_message(parent_label: str, result: dict[str, Any]) -> str:
    child_label = str(result.get("meaning") or "名前のないポワン").strip() or "名前のないポワン"
    status = str(result.get("status") or "").strip() or "unknown"
    dispatch_session_id = str(result.get("dispatchSessionId") or "").strip()
    dispatch_id = result.get("dispatchId")
    conversation_id = result.get("conversationId")
    assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
    reply_text = str((assistant_message or {}).get("text") or "").strip()
    error_text = str(result.get("error") or "").strip()
    lines = [
        f"子ポワン「{child_label}」から、親ポワン「{parent_label}」へ返事が戻りました。",
        "",
        f"状態: {status}",
    ]
    if conversation_id is not None:
        lines.append(f"子会話ID: {conversation_id}")
    if dispatch_session_id:
        lines.append(f"一括指示ID: {dispatch_session_id}")
    if dispatch_id is not None:
        lines.append(f"送信ID: {dispatch_id}")
    if reply_text:
        lines.extend(["", "--- 子ポワンの返事 ---", reply_text])
    elif error_text:
        lines.extend(["", "--- エラー ---", error_text])
    else:
        lines.extend(["", "子ポワンの返事本文はありません。"])
    return "\n".join(lines).strip()


def render_child_return_bundle_message(parent_label: str, results: list[dict[str, Any]], dispatch_session_id: str) -> str:
    lines: list[str] = []
    for index, result in enumerate(results, start=1):
        child_label = str(result.get("meaning") or "名前のないポワン").strip() or "名前のないポワン"
        status = str(result.get("status") or "").strip() or "unknown"
        conversation_id = result.get("conversationId")
        dispatch_id = result.get("dispatchId")
        assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
        reply_text = str((assistant_message or {}).get("text") or "").strip()
        error_text = str(result.get("error") or "").strip()
        lines.extend(["", f"## {index}. {child_label}", f"状態: {status}"])
        if conversation_id is not None:
            lines.append(f"子会話ID: {conversation_id}")
        if dispatch_id is not None:
            lines.append(f"送信ID: {dispatch_id}")
        if reply_text:
            lines.extend(["", reply_text])
        elif error_text:
            lines.extend(["", f"エラー: {error_text}"])
        else:
            lines.extend(["", "返事本文なし。"])
    return "\n".join(lines).strip()


def child_command_skip_reason(item: ChildCommandRequest) -> str:
    if item.skip:
        return item.skipReason.strip() or "skip=true"
    status = str(getattr(item, "status", "") or "").strip().lower()
    if status in {"skip", "skipped", "noop", "no-op", "none"}:
        return item.skipReason.strip() or f"status={status}"
    instruction = item.instruction.strip()
    if "今回の修正対象ではありません" in instruction:
        return "not target"
    if "作業不要" in instruction and "現状維持" in instruction:
        return "no work requested"
    return ""


def child_command_jobs(document: dict[str, Any], parent_id: str, request: CommandChildrenRequest) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    parent = document_node(document, parent_id)
    children = document_direct_children(document, parent_id)
    if not children:
        raise HTTPException(status_code=400, detail="Child powans are required")
    common_instruction = request.instruction.strip()
    jobs_by_id: dict[str, dict[str, str]] = {}
    skipped_by_id: dict[str, dict[str, str]] = {}
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
        skip_reason = child_command_skip_reason(item)
        if skip_reason:
            jobs_by_id.pop(child_id, None)
            skipped_by_id[child_id] = {
                "nodeId": child_id,
                "meaning": powan_label(child),
                "instruction": item.instruction.strip(),
                "skipReason": skip_reason,
            }
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
        if skipped_by_id:
            return [], list(skipped_by_id.values())
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
    return jobs, list(skipped_by_id.values())


@app.get("/api/conversation-history")
def list_conversation_history(project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    STORE.load_document(project, file)
    return STORE.list_document_conversation_sessions(project, file)


@app.get("/api/bulk-conversation-history")
def list_bulk_conversation_history(project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    STORE.load_document(project, file)
    return STORE.list_bulk_command_sessions(project, file)


@app.post("/api/bulk-conversation-history")
def upsert_bulk_conversation_history(request: BulkCommandHistoryRequest) -> dict[str, Any]:
    STORE.load_document(request.project, request.file)
    return STORE.upsert_bulk_command_session(
        request.project,
        request.file,
        request.id,
        request.targetIds,
        request.targetNames,
        [base_model_payload(message) for message in request.messages],
        created_at=request.createdAt,
        updated_at=request.updatedAt,
    )


@app.get("/api/conversation-events")
def stream_conversation_events(project: str, file: str = DEFAULT_FILE) -> StreamingResponse:
    safe_project = STORE.safe_project_name(project)
    safe_file = STORE.safe_powan_name(file)
    subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=200)
    with CONVERSATION_EVENT_SUBSCRIBERS_LOCK:
        CONVERSATION_EVENT_SUBSCRIBERS.add(subscriber)

    def event_stream() -> Iterator[str]:
        try:
            yield ": connected\n\n"
            while True:
                try:
                    payload = subscriber.get(timeout=15)
                except queue.Empty:
                    yield ": ping\n\n"
                    continue
                if payload.get("project") != safe_project or payload.get("file") != safe_file:
                    continue
                yield conversation_sse_frame(payload)
        finally:
            with CONVERSATION_EVENT_SUBSCRIBERS_LOCK:
                CONVERSATION_EVENT_SUBSCRIBERS.discard(subscriber)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/conversations/{node_id}")
def list_conversation_messages(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return live_conversation_payload(project, file, node_id)


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
    return live_conversation_payload(project, file, node_id, conversation_id)


@app.get("/api/agent-runs/running")
def list_running_agent_runs(project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    STORE.load_document(project, file)
    runs = reconcile_running_agent_runs(project, file)
    return {"runs": runs, "count": len(runs)}


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
    project_root_path = sync_codex_workspace(project)
    settings = load_app_settings()
    codex_model = normalize_codex_model(settings.get("codexModel"))
    codex_reasoning_effort = normalize_codex_reasoning_effort(settings.get("codexReasoningEffort"))
    log_server_event(
        "info",
        "conversation-summary-start",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": old_conversation["id"],
            "messageCount": len(messages),
            "codexModel": codex_model,
            "codexReasoningEffort": codex_reasoning_effort,
            "codexWorkspace": str(project_root_path),
        },
    )
    try:
        result = CODEX_BRIDGE.summarize_conversation(
            project_root=project_root_path,
            project=STORE.safe_project_name(project),
            document_name=STORE.safe_powan_name(file),
            node_id=node_id,
            messages=messages,
            codex_model=codex_model,
            codex_reasoning_effort=codex_reasoning_effort,
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
    active_key = f"{STORE.safe_project_name(request.project)}\n{STORE.safe_powan_name(request.file)}\n{node_id}"
    parent_label = "名前のないポワン"
    parent_conversation_id = 0
    job_count = 0
    dispatch_session_id = ""
    release_active_key_in_finally = False
    try:
        document = STORE.load_document(request.project, request.file)
        parent = document_node(document, node_id)
        parent_label = powan_label(parent)
        request_origin_chain = normalize_origin_chain(request.originChain)
        parent_conversation = STORE.active_conversation(request.project, request.file, node_id)
        parent_conversation_id = int(parent_conversation["id"])
        jobs, skipped_jobs = child_command_jobs(document, node_id, request)
        job_count = len(jobs)
        skipped_results = [
            {
                "nodeId": item["nodeId"],
                "meaning": item["meaning"],
                "instruction": item.get("instruction", ""),
                "renderedText": "",
                "status": "skipped",
                "skipReason": item.get("skipReason", ""),
            }
            for item in skipped_jobs
        ]
        log_server_event(
            "info",
            "command-child-powans-jobs-prepared",
            {
                "console": True,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "jobCount": job_count,
                "skippedCount": len(skipped_results),
                "originDepth": len(request_origin_chain),
                "jobs": [
                    {
                        "index": index,
                        "nodeId": job["nodeId"],
                        "meaning": job["meaning"],
                        "instructionLength": len(job["instruction"]),
                        "renderedTextLength": len(job["text"]),
                    }
                    for index, job in enumerate(jobs)
                ],
                "skipped": skipped_results,
            },
        )
        if skipped_results and not jobs:
            response_payload = {
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "parent": {
                    "id": node_id,
                    "meaning": parent_label,
                },
                "detached": False,
                "results": skipped_results,
            }
            log_server_event(
                "info",
                "command-child-powans-all-skipped",
                {
                    "console": True,
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "nodeId": node_id,
                    "meaning": parent_label,
                    "skippedCount": len(skipped_results),
                    "results": skipped_results,
                },
            )
            record_api_action_safely(
                project=request.project,
                file=request.file,
                node_id=node_id,
                action="command-children",
                status="completed",
                request_payload=request_payload,
                response_payload=response_payload,
            )
            return response_payload
        with COMMAND_CHILDREN_ACTIVE_LOCK:
            if active_key in COMMAND_CHILDREN_ACTIVE_KEYS:
                log_server_event(
                    "warn",
                    "command-child-powans-duplicate-rejected",
                    {
                        "console": True,
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "nodeId": node_id,
                        "message": "command-children already running for this parent",
                        "request": request_payload,
                    },
                )
                record_api_action_safely(
                    project=request.project,
                    file=request.file,
                    node_id=node_id,
                    action="command-children",
                    status="failed",
                    request_payload=request_payload,
                    response_payload={},
                    error_text="command-children already running for this parent",
                )
                raise HTTPException(status_code=409, detail="command-children already running for this parent")
            COMMAND_CHILDREN_ACTIVE_KEYS.add(active_key)
            release_active_key_in_finally = True
        dispatch_session_id = f"childcmd-{uuid4().hex}"
        dispatch_interval_ms = 100
        worker_count = max(1, len(jobs))
        STORE.create_child_command_session(
            request.project,
            request.file,
            dispatch_session_id,
            node_id,
            request.instruction,
            request_payload,
            len(jobs),
        )
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
                "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                "originDepth": len(request_origin_chain),
                "dispatchSessionId": dispatch_session_id,
                "dispatchIntervalMs": dispatch_interval_ms,
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
                "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                "dispatchSessionId": dispatch_session_id,
                "dispatchIntervalMs": dispatch_interval_ms,
                "originDepth": len(request_origin_chain),
            },
        )

        for job in jobs:
            child_conversation = STORE.active_conversation(request.project, request.file, job["nodeId"])
            log_powan_work_status(
                "received",
                project=request.project,
                file=request.file,
                source="command-children",
                sender_id=node_id,
                sender_label=parent_label,
                receiver_id=job["nodeId"],
                receiver_label=job["meaning"],
                conversation_id=child_conversation["id"],
                extra={
                    "textPreview": compact_console_text(job["text"]),
                    "messageLength": len(job["text"].strip()),
                    "includeMeaningTree": bool(request.includeMeaningTree),
                    "includeDirectChildCode": False,
                    "attachmentCount": 0,
                    "preStored": True,
                },
            )
            user_message = STORE.append_conversation_message(
                request.project,
                request.file,
                job["nodeId"],
                "user",
                conversation_record_text(job["text"], []),
            )
            log_server_event(
                "info",
                "powan-user-message-appended",
                {
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "nodeId": job["nodeId"],
                    "conversationId": child_conversation["id"],
                    "messageId": user_message.get("id"),
                    "source": "command-children",
                    "senderNodeId": node_id,
                    "messageLength": len(job["text"].strip()),
                    "preStored": True,
                },
            )
            job["conversationId"] = child_conversation["id"]
            job["userMessage"] = user_message
            dispatch = STORE.record_child_command_dispatch(
                request.project,
                request.file,
                dispatch_session_id,
                node_id,
                job["nodeId"],
                job["meaning"],
                job["instruction"],
                job["text"],
                int(child_conversation["id"]),
                int(user_message["id"]),
            )
            job["dispatchId"] = dispatch["id"]
            job["originChain"] = append_origin_hop(
                request_origin_chain,
                origin_hop(
                    from_id=node_id,
                    from_name=parent_label,
                    to_id=job["nodeId"],
                    to_name=job["meaning"],
                    dispatch_session_id=dispatch_session_id,
                    dispatch_id=dispatch.get("id"),
                    instruction=job["instruction"],
                ),
            )
            parent_log_message = emit_conversation_event(
                project=request.project,
                file=request.file,
                node_id=node_id,
                conversation_id=parent_conversation_id,
                kind="child_command_sent",
                role="system",
                text=render_parent_child_command_log(
                    parent_label=parent_label,
                    child_label=job["meaning"],
                    instruction=job["instruction"],
                    rendered_text=job["text"],
                    dispatch_session_id=dispatch_session_id,
                    dispatch_id=dispatch.get("id"),
                ),
                receiver_label=parent_label,
                source="command-children",
                metadata={
                    "childId": job["nodeId"],
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": dispatch.get("id"),
                },
            )
            log_server_event(
                "info",
                "command-child-parent-tab-log-appended",
                {
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "parentId": node_id,
                    "childId": job["nodeId"],
                    "conversationId": parent_conversation_id,
                    "messageId": parent_log_message.get("id"),
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": dispatch.get("id"),
                },
            )
        STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "sent")

        def append_parent_child_return_message(results: list[dict[str, Any]]) -> dict[str, Any] | None:
            reportable_results = [result for result in results if child_result_should_return_to_parent(result)]
            if not reportable_results:
                log_server_event(
                    "info",
                    "command-child-return-skipped-delegated-only",
                    {
                        "console": True,
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "parentLabel": parent_label,
                        "dispatchSessionId": dispatch_session_id,
                        "resultCount": len(results),
                    },
                )
                return None
            parent_text = render_child_return_bundle_message(parent_label, reportable_results, dispatch_session_id)
            if not parent_text:
                return None
            parent_message = emit_conversation_event(
                project=request.project,
                file=request.file,
                node_id=node_id,
                conversation_id=parent_conversation_id,
                kind="child_report_returned",
                role="user",
                text=parent_text,
                receiver_label=parent_label,
                source="command-child-return",
                metadata={"dispatchSessionId": dispatch_session_id},
            )
            for result in reportable_results:
                child_node_id = str(result.get("nodeId") or "").strip()
                child_conversation_id = result.get("conversationId")
                if not child_node_id or child_conversation_id is None:
                    continue
                try:
                    child_log_message = emit_conversation_event(
                        project=request.project,
                        file=request.file,
                        node_id=child_node_id,
                        conversation_id=int(child_conversation_id),
                        kind="child_report_returned",
                        role="system",
                        text=render_child_parent_return_log(parent_label, result),
                        receiver_label=str(result.get("meaning") or "名前のないポワン"),
                        source="command-child-return",
                        metadata={
                            "parentId": node_id,
                            "dispatchSessionId": dispatch_session_id,
                            "dispatchId": result.get("dispatchId"),
                        },
                    )
                    log_server_event(
                        "info",
                        "command-child-return-child-tab-log-appended",
                        {
                            "project": STORE.safe_project_name(request.project),
                            "file": STORE.safe_powan_name(request.file),
                            "parentId": node_id,
                            "childId": child_node_id,
                            "conversationId": int(child_conversation_id),
                            "messageId": child_log_message.get("id"),
                            "dispatchSessionId": dispatch_session_id,
                            "dispatchId": result.get("dispatchId"),
                        },
                    )
                except Exception as exc:
                    log_server_event(
                        "warn",
                        "command-child-return-child-tab-log-failed",
                        {
                            "project": STORE.safe_project_name(request.project),
                            "file": STORE.safe_powan_name(request.file),
                            "parentId": node_id,
                            "childId": child_node_id,
                            "conversationId": child_conversation_id,
                            "dispatchSessionId": dispatch_session_id,
                            "error": repr(exc),
                        },
                    )
            sender_id = str(reportable_results[0].get("nodeId") or "") if len(reportable_results) == 1 else None
            incoming_message = child_return_incoming_message(
                parent_id=node_id,
                parent_label=parent_label,
                parent_conversation_id=int(parent_conversation_id),
                parent_message_id=int(parent_message["id"]) if parent_message.get("id") is not None else None,
                parent_text=parent_text,
                results=reportable_results,
                continue_after_child_replies=bool(request.continueAfterChildReplies),
                dispatch_session_id=dispatch_session_id,
            )
            downstream_reports = build_downstream_origin_reports(
                base_chain=request_origin_chain,
                parent_id=node_id,
                parent_label=parent_label,
                results=reportable_results,
                dispatch_session_id=dispatch_session_id,
            )
            queue_source = "command-child-return"
            if downstream_reports:
                required_judgement = build_required_origin_judgement(
                    judge_id=node_id,
                    judge_label=parent_label,
                    origin_chain=request_origin_chain,
                    downstream_reports=downstream_reports,
                    report_text=parent_text,
                    dispatch_session_id=dispatch_session_id,
                )
                attach_origin_judgement(incoming_message, required_judgement=required_judgement)
                queue_source = "origin-report-judgement"
                log_server_event(
                    "info",
                    "origin-report-created-from-child-return",
                    {
                        "console": True,
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "parentLabel": parent_label,
                        "dispatchSessionId": dispatch_session_id,
                        "originDepth": len(request_origin_chain),
                        "downstreamCount": len(downstream_reports),
                        "parentMessageId": parent_message.get("id"),
                    },
                )
            STORE.queue_pending_codex_message(
                request.project,
                request.file,
                node_id,
                int(parent_conversation_id),
                int(parent_message["id"]),
                source=queue_source,
                sender_id=sender_id,
                sender_label="子ポワン一括返答",
                payload=incoming_message,
            )
            schedule_pending_codex_drain(
                request.project,
                request.file,
                node_id,
                reason="child-command-return-queued",
            )
            return {
                "text": parent_text,
                "message": parent_message,
                "senderId": sender_id,
                "incomingMessage": incoming_message,
            }

        def run_job(index: int, job: dict[str, Any]) -> dict[str, Any]:
            delay_ms = dispatch_interval_ms * index
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
                if job.get("dispatchId") is not None:
                    STORE.mark_child_command_dispatch_started(request.project, int(job["dispatchId"]))
                log_server_event(
                    "info",
                    "command-child-powan-before-run",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "parentMeaning": parent_label,
                        "nodeId": job["nodeId"],
                        "meaning": job["meaning"],
                        "index": index,
                        "delayMs": delay_ms,
                        "renderedTextLength": len(job["text"]),
                        "instructionLength": len(job["instruction"]),
                        "dispatchSessionId": dispatch_session_id,
                        "dispatchId": job.get("dispatchId"),
                        "dispatchIntervalMs": dispatch_interval_ms,
                        "originDepth": len(normalize_origin_chain(job.get("originChain"))),
                    },
                )
                child_origin_chain = normalize_origin_chain(job.get("originChain"))
                child_incoming_message = build_incoming_message_payload(
                    source="command-children",
                    text=job["text"],
                    sender_node_id=node_id,
                    sender_label=parent_label,
                    receiver_node_id=job["nodeId"],
                    receiver_label=job["meaning"],
                    conversation_id=int(job.get("conversationId") or 0),
                    user_message_id=int((job.get("userMessage") or {}).get("id")) if isinstance(job.get("userMessage"), dict) and (job.get("userMessage") or {}).get("id") is not None else None,
                    command_children_context={
                        "dispatchSessionId": dispatch_session_id,
                        "dispatchId": job.get("dispatchId"),
                    },
                )
                child_incoming_message["originChain"] = child_origin_chain
                child_incoming_message["originRoute"] = {
                    "kind": "parent_command",
                    "originChain": child_origin_chain,
                    "reportBackOnComplete": False,
                }
                result = run_powan_codex_message(
                    job["nodeId"],
                    project=request.project,
                    file=request.file,
                    text=job["text"],
                    include_meaning_tree=bool(request.includeMeaningTree),
                    attachments=[],
                    source="command-children",
                    sender_node_id=node_id,
                    pre_appended_user_message=job.get("userMessage") if isinstance(job.get("userMessage"), dict) else None,
                    incoming_message=child_incoming_message,
                )
                delegated = bool(result.get("earlyCompleted")) and str(result.get("earlyCompleteReason") or "") == "command_children_accepted"
                if delegated:
                    run_status = "delegated"
                else:
                    run_status = "cancelled" if result.get("cancelled") else "completed"
                item = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": run_status,
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": job.get("dispatchId"),
                    "conversationId": result.get("conversationId"),
                    "userMessage": result.get("userMessage"),
                    "assistantMessage": result.get("assistantMessage"),
                    "agentRun": result.get("agentRun"),
                    "earlyCompleted": bool(result.get("earlyCompleted")),
                    "earlyCompleteReason": str(result.get("earlyCompleteReason") or ""),
                }
                if job.get("dispatchId") is not None:
                    assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
                    agent_run = result.get("agentRun") if isinstance(result.get("agentRun"), dict) else None
                    STORE.mark_child_command_dispatch_replied(
                        request.project,
                        int(job["dispatchId"]),
                        run_status,
                        int(assistant_message["id"]) if assistant_message and assistant_message.get("id") is not None else None,
                        int(agent_run["id"]) if agent_run and agent_run.get("id") is not None else None,
                    )
                item["parentReturnText"] = render_child_return_message(parent_label, item)
                log_server_event(
                    "trace",
                    "command-child-powan-job-complete",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "nodeId": job["nodeId"],
                        "index": index,
                        "status": run_status,
                        "dispatchSessionId": dispatch_session_id,
                        "dispatchId": job.get("dispatchId"),
                    },
                )
                return item
            except HTTPException as exc:
                if job.get("dispatchId") is not None:
                    STORE.mark_child_command_dispatch_replied(request.project, int(job["dispatchId"]), "failed", error_text=str(exc.detail))
                failure = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": "failed",
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": job.get("dispatchId"),
                    "conversationId": job.get("conversationId"),
                    "userMessage": job.get("userMessage"),
                    "error": exc.detail,
                    "httpStatus": exc.status_code,
                }
                failure["parentReturnText"] = render_child_return_message(parent_label, failure)
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
                if job.get("dispatchId") is not None:
                    STORE.mark_child_command_dispatch_replied(request.project, int(job["dispatchId"]), "failed", error_text=repr(exc))
                failure = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": "failed",
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": job.get("dispatchId"),
                    "conversationId": job.get("conversationId"),
                    "userMessage": job.get("userMessage"),
                    "error": repr(exc),
                    "httpStatus": 500,
                }
                failure["parentReturnText"] = render_child_return_message(parent_label, failure)
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

        def run_batch_detached() -> None:
            results: list[dict[str, Any]] = []
            try:
                ordered_results: list[dict[str, Any] | None] = [None] * len(jobs)
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    futures = {
                        executor.submit(run_job, index, job): index
                        for index, job in enumerate(jobs)
                    }
                    for future in as_completed(futures):
                        index = futures[future]
                        ordered_results[index] = future.result()
                results = [result for result in ordered_results if result is not None]

                for result in results:
                    result.pop("httpStatus", None)

                failed_count = sum(1 for result in results if result.get("status") in {"failed", "cancelled"})
                delegated_count = sum(1 for result in results if result.get("status") == "delegated")
                if failed_count:
                    session_status = "failed"
                elif delegated_count:
                    session_status = "delegated"
                else:
                    session_status = "completed"
                response = {
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "parent": {"id": node_id, "meaning": powan_label(parent)},
                    "detached": True,
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchIntervalMs": dispatch_interval_ms,
                    "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                    "results": results,
                }
                complete_label = "一括命令委譲" if session_status == "delegated" else "一括命令完了"
                complete_message = f"{parent_label} -> 子ポワン {len(results)}件 / {complete_label}"
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
                        "failed": failed_count,
                        "delegated": delegated_count,
                        "sessionStatus": session_status,
                        "instructionPreview": compact_console_text(request.instruction),
                        "request": request_payload,
                        "response": response,
                    },
                )
                STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, session_status)
                remember_powan_batch_work_event(
                    status=session_status,
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
                        "detached": True,
                        "failed": failed_count,
                        "delegated": delegated_count,
                        "dispatchSessionId": dispatch_session_id,
                        "dispatchIntervalMs": dispatch_interval_ms,
                        "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                    },
                )
                with COMMAND_CHILDREN_ACTIVE_LOCK:
                    COMMAND_CHILDREN_ACTIVE_KEYS.discard(active_key)
                parent_return = append_parent_child_return_message(results)
                if parent_return:
                    log_server_event(
                        "info",
                        "command-child-powans-parent-followup-queued",
                        {
                            "console": True,
                            "project": STORE.safe_project_name(request.project),
                            "file": STORE.safe_powan_name(request.file),
                            "parentId": node_id,
                            "parentMeaning": parent_label,
                            "parentConversationId": parent_conversation_id,
                            "dispatchSessionId": dispatch_session_id,
                            "parentMessageId": (parent_return.get("message") or {}).get("id") if isinstance(parent_return, dict) else None,
                        },
                    )
                else:
                    log_server_event(
                        "info",
                        "command-child-powans-parent-followup-skipped",
                        {
                            "console": True,
                            "project": STORE.safe_project_name(request.project),
                            "file": STORE.safe_powan_name(request.file),
                            "parentId": node_id,
                            "parentMeaning": parent_label,
                            "parentConversationId": parent_conversation_id,
                            "dispatchSessionId": dispatch_session_id,
                            "reason": "delegated-only",
                        },
                    )
            except Exception as exc:
                STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "failed")
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
                    extra={"detached": True, "error": repr(exc)},
                )
            finally:
                with COMMAND_CHILDREN_ACTIVE_LOCK:
                    COMMAND_CHILDREN_ACTIVE_KEYS.discard(active_key)

        accepted_results = [
            {
                "nodeId": job["nodeId"],
                "meaning": job["meaning"],
                "instruction": job["instruction"],
                "renderedText": job["text"],
                "dispatchSessionId": dispatch_session_id,
                "dispatchId": job.get("dispatchId"),
                "conversationId": job.get("conversationId"),
                "userMessage": job.get("userMessage"),
                "status": "accepted",
            }
            for job in jobs
        ] + skipped_results
        accepted_response = {
            "project": STORE.safe_project_name(request.project),
            "file": STORE.safe_powan_name(request.file),
            "parent": {"id": node_id, "meaning": powan_label(parent)},
            "detached": True,
            "dispatchSessionId": dispatch_session_id,
            "dispatchIntervalMs": dispatch_interval_ms,
            "continueAfterChildReplies": bool(request.continueAfterChildReplies),
            "results": accepted_results,
            "skippedCount": len(skipped_results),
        }
        log_server_event(
            "info",
            "command-child-powans-accepted",
            {
                "console": True,
                "message": f"{parent_label} -> 子ポワン {len(jobs)}件 / 一括命令受付完了",
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "count": len(jobs),
                "skippedCount": len(skipped_results),
                "detached": True,
                "dispatchSessionId": dispatch_session_id,
                "dispatchIntervalMs": dispatch_interval_ms,
                "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                "request": request_payload,
                "response": accepted_response,
            },
        )
        record_api_action_safely(
            project=request.project,
            file=request.file,
            node_id=node_id,
            action="command-children",
            status="accepted",
            request_payload=request_payload,
            response_payload=accepted_response,
        )
        release_active_key_in_finally = False
        threading.Thread(
            target=run_batch_detached,
            name=f"abc-command-children-{node_id}",
            daemon=True,
        ).start()
        return accepted_response
    except HTTPException as exc:
        if dispatch_session_id:
            STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "failed")
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
        if dispatch_session_id:
            STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "failed")
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
    finally:
        if release_active_key_in_finally:
            with COMMAND_CHILDREN_ACTIVE_LOCK:
                COMMAND_CHILDREN_ACTIVE_KEYS.discard(active_key)


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
